"""Ingest frame thi online: hàng đợi + worker infer riêng cho từng phiên con.
Luồng chính: browser POST frame -> queue (giữ mới nhất) -> worker process_frame ->
debounce -> snapshot 30s (tái dùng _save_snapshot/calculate_stats của pipeline).
"""

import secrets
import threading
import time
from collections import deque
from datetime import datetime, timezone
from queue import Queue

import cv2
import numpy as np

from ai_model import ai_pipeline
from ai_model.ai_pipeline import _last_pose_info, process_frame
from core.config import settings
from core.logger import get_logger
from crud.session_crud import end_session, get_session_by_id
from database.database import SessionLocal
from service.pipeline_service import (
    CHEAT_MIN_HITS,
    CHEAT_WINDOW,
    SAVE_INTERVAL_SECONDS,
    _save_snapshot,
    calculate_stats,
)

logger = get_logger(__name__)

# Giới hạn ingest chống spam/dồn khi mạng về
MAX_JPG_BYTES = 500 * 1024
QUEUE_MAXLEN = 3
TS_SKEW_SECONDS = 60
ABSENT_SECONDS = 10
IDLE_STOP_SECONDS = 120

# token nộp bài -> session_id (mất khi restart, join lại là có token mới)
_tokens: dict[str, int] = {}
_tokens_lock = threading.Lock()

# session_id -> _SessionWorker
_workers: dict[int, "_SessionWorker"] = {}
_workers_lock = threading.Lock()


def _window_ok(deq: deque, window: int = CHEAT_WINDOW, hits: int = CHEAT_MIN_HITS) -> bool:
    """Debounce 3/5 như CameraState nhưng cho worker độc lập."""
    recent = list(deq)[-window:]
    return len(recent) >= hits and sum(1 for v in recent if v) >= hits


def mint_token(session_id: int) -> str:
    """Cấp token nộp frame cho phiên con."""
    token = secrets.token_urlsafe(24)
    with _tokens_lock:
        _tokens[token] = session_id
    return token


def resolve_token(token: str) -> int | None:
    """Tra session_id từ token nộp bài."""
    with _tokens_lock:
        return _tokens.get(token)


def revoke_session_tokens(session_id: int) -> None:
    """Thu hồi mọi token của phiên (khi kết thúc ca)."""
    with _tokens_lock:
        for tok in [t for t, sid in _tokens.items() if sid == session_id]:
            _tokens.pop(tok, None)


class _SessionWorker:
    """Worker infer cho một phiên con thi online."""

    def __init__(self, session_id: int):
        self.session_id = session_id
        self.ns = f"ingest-{session_id}"
        self.queue: Queue = Queue(maxsize=QUEUE_MAXLEN)
        self.cheat_window: deque = deque(maxlen=10)
        self.behavior_window: deque = deque(maxlen=10)
        self.recent: deque = deque(maxlen=10)
        self.frame_count = 0
        self.last_save = 0.0
        self.last_seen_person = time.time()
        self.vang_fired = False
        self.last_activity = time.time()
        self.latest_jpeg: bytes | None = None
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def push(self, jpg: bytes) -> bool:
        """Đẩy frame vào hàng đợi, đầy thì bỏ cũ nhất giữ mới nhất."""
        while self.queue.full():
            try:
                self.queue.get_nowait()
            except Exception:
                break
        try:
            self.queue.put_nowait((jpg, time.time()))
            self.last_activity = time.time()
            return True
        except Exception:
            return False

    def _loop(self) -> None:
        db = SessionLocal()
        try:
            image_dir = settings.IMAGE_DIR
            image_dir.mkdir(parents=True, exist_ok=True)
            while self.running:
                try:
                    jpg, _ = self.queue.get(timeout=1.0)
                except Exception:
                    if self._should_stop(db):
                        break
                    continue
                try:
                    arr = np.frombuffer(jpg, dtype=np.uint8)
                    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                    if frame is None:
                        continue
                    self.frame_count += 1
                    annotated, results = process_frame(
                        frame, self.frame_count, tracker_ns=self.ns
                    )
                    ok, buf = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 75])
                    if ok:
                        self.latest_jpeg = buf.tobytes()
                    self.recent.append((annotated, list(results)))
                    self._note_windows(results)
                    if time.time() - self.last_save > SAVE_INTERVAL_SECONDS:
                        self._snapshot(db, annotated, results, image_dir)
                        self.last_save = time.time()
                except Exception as exc:
                    logger.debug(f"Ingest worker #{self.session_id} failed: {exc}")
        finally:
            db.close()
            with _workers_lock:
                _workers.pop(self.session_id, None)
            logger.info(f"Ingest worker stopped for session {self.session_id}")

    def _note_windows(self, results: list[dict]) -> None:
        """Cập nhật debounce vật/hành vi + luật vắng mặt/nhiều người."""
        n_persons, _ = _last_pose_info.get(self.ns, (0, 0.0))
        now = time.time()
        if n_persons > 0:
            self.last_seen_person = now
            self.vang_fired = False
        absent_long = n_persons == 0 and (now - self.last_seen_person) > ABSENT_SECONDS

        has_cheat = any(
            r.get("is_cheat") and r.get("kind", "object") == "object" for r in results
        )
        has_behavior = any(r.get("kind") == "behavior" for r in results)
        self.cheat_window.append(bool(has_cheat))
        self.behavior_window.append(bool(has_behavior or absent_long))

        if n_persons > 1:
            _, max_conf = _last_pose_info.get(self.ns, (0, 0.0))
            results.append({
                "bbox": [],
                "mask": None,
                "label": "nhieu_nguoi",
                "confidence": round(max_conf or 0.9, 4),
                "is_cheat": True,
                "kind": "behavior",
            })

    def _snapshot(self, db, annotated, results, image_dir) -> None:
        """Chọn frame gần nhất có cheat rồi lưu snapshot (logic như pipeline)."""
        for frm, res in reversed(list(self.recent)):
            if any(r.get("is_cheat") for r in res):
                annotated, results = frm, list(res)
                break
        kept: list[dict] = []
        for r in results:
            if not r.get("is_cheat"):
                kept.append(r)
                continue
            if r.get("kind") == "behavior":
                if r.get("label") == "quay_sau":
                    kept.append(r)
                elif _window_ok(self.behavior_window):
                    kept.append(r)
                continue
            if _window_ok(self.cheat_window):
                kept.append(r)
        # vang_mat: chỉ ghi 1 lần cho mỗi đợt vắng, khi đã debounce đủ
        now = time.time()
        n_persons, _ = _last_pose_info.get(self.ns, (0, 0.0))
        if (
            n_persons == 0
            and (now - self.last_seen_person) > ABSENT_SECONDS
            and not self.vang_fired
            and _window_ok(self.behavior_window)
        ):
            kept.append({
                "bbox": [],
                "mask": None,
                "label": "vang_mat",
                "confidence": 0.9,
                "is_cheat": True,
                "kind": "behavior",
            })
            self.vang_fired = True
        _save_snapshot(db, self.session_id, annotated, kept, image_dir, self.frame_count)

    def _should_stop(self, db) -> bool:
        """Dừng worker khi phiên kết thúc hoặc quá lâu không có frame."""
        if time.time() - self.last_activity > IDLE_STOP_SECONDS:
            self.running = False
            return True
        try:
            s = get_session_by_id(db, self.session_id)
            if s is None or s.TrangThai != "dang_giam_sat":
                self.running = False
                return True
        except Exception:
            pass
        return False


def ensure_worker(session_id: int) -> "_SessionWorker":
    """Lấy hoặc tạo worker cho phiên con (an toàn luồng)."""
    with _workers_lock:
        worker = _workers.get(session_id)
        if worker is None or not worker.running:
            worker = _SessionWorker(session_id)
            _workers[session_id] = worker
        return worker


def ingest_frame(session_id: int, token: str, ts_client: float, jpg: bytes) -> tuple[bool, str]:
    """Nhận frame từ browser: check token, skew, định dạng rồi xếp hàng.
    Trả về (ok, lý do)."""
    if resolve_token(token) != session_id:
        return False, "token không hợp lệ"
    if abs(time.time() - ts_client) > TS_SKEW_SECONDS:
        return False, "timestamp lệch quá 60s (nghi replay)"
    if not jpg or len(jpg) > MAX_JPG_BYTES:
        return False, "kích thước ảnh không hợp lệ"
    if len(jpg) < 3 or jpg[0] != 0xFF or jpg[1] != 0xD8 or jpg[2] != 0xFF:
        return False, "không phải JPEG"
    worker = ensure_worker(session_id)
    if not worker.push(jpg):
        return False, "hàng đợi bận"
    return True, "queued"


def stop_session_workers(session_id: int) -> None:
    """Dừng worker khi chốt phiên + thu hồi token."""
    with _workers_lock:
        worker = _workers.get(session_id)
    if worker:
        worker.running = False
    revoke_session_tokens(session_id)
    ai_pipeline.reset_tracker(f"ingest-{session_id}")


def get_latest_frame(session_id: int) -> bytes | None:
    """Lấy frame JPEG đã qua AI mới nhất của phiên con (nếu worker đang chạy)."""
    with _workers_lock:
        worker = _workers.get(session_id)
        if worker and worker.latest_jpeg:
            return worker.latest_jpeg
    return None
