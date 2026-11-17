"""Ingest frame thi online: hàng đợi + worker infer riêng cho từng luồng camera.

Mỗi phiên con có thể có 2 luồng:
- front: webcam máy tính (pose + object + vắng mặt/nhiều người)
- side : điện thoại đặt sau/bên (chỉ object detection)

Luồng chính: browser POST frame (kèm vai_tro) -> xác thực token theo stream ->
queue giữ frame mới nhất -> worker infer -> debounce -> snapshot bằng chứng +
snapshot nền (raw -> normalized -> tbl_snapshot/tbl_snapshot_processed).
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
from service import snapshot_service
from service.camera_state import (
    OBJECT_COOLDOWN_SECONDS,
    POSE_COOLDOWN_SECONDS,
    POSE_MIN_HITS,
    POSE_WINDOW,
)
from service.pipeline_service import (
    CHEAT_MIN_HITS,
    CHEAT_WINDOW,
    SAVE_INTERVAL_SECONDS,
    _save_snapshot,
)

logger = get_logger(__name__)

# Giới hạn ingest chống spam/dồn khi mạng về
MAX_JPG_BYTES = 500 * 1024
QUEUE_MAXLEN = 3
TS_SKEW_SECONDS = 60
ABSENT_SECONDS = 10
IDLE_STOP_SECONDS = 120

ROLE_FRONT = "front"
ROLE_SIDE = "side"
VALID_ROLES = {ROLE_FRONT, ROLE_SIDE}
ROLE_LABELS = {ROLE_FRONT: "Camera trước", ROLE_SIDE: "Camera phụ"}

# token nộp frame -> (session_id, vai_tro). Cache RAM, DB là nguồn bền vững.
_tokens: dict[str, tuple[int, str]] = {}
_tokens_lock = threading.Lock()

# (session_id, vai_tro) -> _SessionWorker
_workers: dict[tuple[int, str], "_SessionWorker"] = {}
_workers_lock = threading.Lock()

TOKEN_INVALID = "token không hợp lệ"


def _normalize_role(vai_tro: str | None) -> str:
    role = (vai_tro or ROLE_FRONT).strip().lower()
    return role if role in VALID_ROLES else ROLE_FRONT


def _window_ok(deq: deque, window: int = CHEAT_WINDOW, hits: int = CHEAT_MIN_HITS) -> bool:
    """Debounce 3/5 như CameraState nhưng cho worker độc lập."""
    recent = list(deq)[-window:]
    return len(recent) >= hits and sum(1 for v in recent if v) >= hits


def mint_token(session_id: int, vai_tro: str = ROLE_FRONT) -> str:
    """Cấp token cho một luồng camera của phiên con.

    Token được lưu trong tbl_camera_stream để sống qua restart/đa tiến trình.
    Với role=front, đồng thời ghi TokenThamGia cũ để tương thích ngược.
    """
    from models.camera_stream import CameraStream
    from models.monitoring_session import MonitoringSession

    role = _normalize_role(vai_tro)
    token = secrets.token_urlsafe(24)
    old_token: str | None = None
    db = SessionLocal()
    try:
        stream = (
            db.query(CameraStream)
            .filter(
                CameraStream.FK_MaPhienGiamSat == session_id,
                CameraStream.VaiTro == role,
            )
            .first()
        )
        if stream is None:
            stream = CameraStream(
                FK_MaPhienGiamSat=session_id,
                VaiTro=role,
                TrangThai="dang_hoat_dong",
            )
            db.add(stream)
            db.flush()
        old_token = stream.Token
        stream.Token = token
        stream.TrangThai = "dang_hoat_dong"
        stream.LanCuoiNhan = datetime.now(timezone.utc)

        if role == ROLE_FRONT:
            row = (
                db.query(MonitoringSession)
                .filter(MonitoringSession.PK_MaPhienGiamSat == session_id)
                .first()
            )
            if row is not None:
                row.TokenThamGia = token

        db.commit()
    finally:
        db.close()

    with _tokens_lock:
        if old_token:
            _tokens.pop(old_token, None)
        _tokens[token] = (session_id, role)
    return token


def resolve_token(token: str) -> tuple[int, str] | None:
    """Tra (session_id, vai_tro) từ token. Miss cache thì đọc DB (restart/tiến trình khác)."""
    with _tokens_lock:
        cached = _tokens.get(token)
    if isinstance(cached, tuple):
        return cached

    from models.camera_stream import CameraStream
    from models.monitoring_session import MonitoringSession

    db = SessionLocal()
    try:
        stream = db.query(CameraStream).filter(CameraStream.Token == token).first()
        if stream is not None:
            resolved = (stream.FK_MaPhienGiamSat, stream.VaiTro)
            with _tokens_lock:
                _tokens[token] = resolved
            return resolved

        # Tương thích token cũ trước khi tách stream: coi là camera trước.
        row = (
            db.query(MonitoringSession)
            .filter(MonitoringSession.TokenThamGia == token)
            .first()
        )
        if row is None:
            return None
        resolved = (row.PK_MaPhienGiamSat, ROLE_FRONT)
        with _tokens_lock:
            _tokens[token] = resolved
        return resolved
    finally:
        db.close()


def revoke_session_tokens(session_id: int) -> None:
    """Thu hồi mọi token stream của phiên (khi kết thúc ca): xóa cache RAM lẫn DB."""
    from models.camera_stream import CameraStream
    from models.monitoring_session import MonitoringSession

    with _tokens_lock:
        for tok, value in list(_tokens.items()):
            sid = value[0] if isinstance(value, tuple) else value
            if sid == session_id:
                _tokens.pop(tok, None)

    db = SessionLocal()
    try:
        streams = (
            db.query(CameraStream)
            .filter(CameraStream.FK_MaPhienGiamSat == session_id)
            .all()
        )
        for stream in streams:
            stream.Token = None
            stream.TrangThai = "ket_thuc"

        rows = (
            db.query(MonitoringSession)
            .filter(MonitoringSession.PK_MaPhienGiamSat == session_id)
            .all()
        )
        for row in rows:
            row.TokenThamGia = None
        db.commit()
    finally:
        db.close()


class _SessionWorker:
    """Worker infer cho một luồng camera (session_id, vai_tro)."""

    def __init__(self, session_id: int, vai_tro: str = ROLE_FRONT):
        self.session_id = session_id
        self.vai_tro = _normalize_role(vai_tro)
        self.ns = f"ingest-{session_id}-{self.vai_tro}"
        self.queue: Queue = Queue(maxsize=QUEUE_MAXLEN)
        self.cheat_window: deque = deque(maxlen=10)
        self.behavior_window: deque = deque(maxlen=10)
        self.recent: deque = deque(maxlen=10)
        self.frame_count = 0
        self.last_save = 0.0
        self.last_object_save = 0.0
        self.last_pose_save = 0.0
        self.last_snapshot_save = 0.0
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
                        frame,
                        self.frame_count,
                        tracker_ns=self.ns,
                        enable_pose=(self.vai_tro == ROLE_FRONT),
                    )
                    ok, buf = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 75])
                    if ok:
                        self.latest_jpeg = buf.tobytes()
                    self.recent.append((annotated, list(results)))
                    self._note_windows(results)

                    now = time.time()
                    has_obj = any(
                        r.get("is_cheat") and r.get("kind", "object") == "object" for r in results
                    )
                    has_beh = (
                        self.vai_tro == ROLE_FRONT
                        and any(r.get("kind") == "behavior" for r in results)
                    )
                    trigger_obj = (
                        has_obj
                        and _window_ok(self.cheat_window, CHEAT_WINDOW, CHEAT_MIN_HITS)
                        and (now - self.last_object_save >= OBJECT_COOLDOWN_SECONDS)
                    )
                    trigger_beh = (
                        has_beh
                        and _window_ok(self.behavior_window, POSE_WINDOW, POSE_MIN_HITS)
                        and (now - self.last_pose_save >= POSE_COOLDOWN_SECONDS)
                    )

                    if trigger_obj or trigger_beh:
                        if trigger_obj:
                            self.last_object_save = now
                        if trigger_beh:
                            self.last_pose_save = now
                        self._snapshot(db, annotated, results, image_dir)
                        self.last_save = now
                    elif now - self.last_save > SAVE_INTERVAL_SECONDS:
                        self._snapshot(db, annotated, results, image_dir)
                        self.last_save = now

                    if (
                        trigger_obj
                        or trigger_beh
                        or now - self.last_snapshot_save >= snapshot_service.SNAPSHOT_INTERVAL_SECONDS
                    ):
                        self._persist_snapshot(jpg, annotated)
                        self.last_snapshot_save = now
                except Exception as exc:
                    logger.debug(f"Ingest worker #{self.session_id}/{self.vai_tro} failed: {exc}")
        finally:
            db.close()
            with _workers_lock:
                key = (self.session_id, self.vai_tro)
                if _workers.get(key) is self:
                    _workers.pop(key, None)
            logger.info(
                f"Ingest worker stopped for session {self.session_id}/{self.vai_tro}"
            )

    def _persist_snapshot(self, raw_jpg: bytes, annotated) -> None:
        """Lưu snapshot nền: raw trước, chuẩn hoá sau, ghi bảng dẫn xuất."""
        try:
            snapshot_service.capture_snapshot(
                self.session_id,
                self.vai_tro,
                raw_jpg,
                annotated_frame=annotated,
            )
        except Exception as exc:
            logger.debug(
                f"Snapshot pipeline failed for session {self.session_id}/{self.vai_tro}: {exc}"
            )

    def _note_windows(self, results: list[dict]) -> None:
        """Cập nhật debounce vật/hành vi + luật vắng mặt/nhiều người.

        Camera phụ chỉ chạy object detection nên không dùng cửa sổ behavior và
        không kích hoạt vang_mat/nhieu_nguoi (tránh báo trùng với camera trước).
        """
        has_cheat = any(
            r.get("is_cheat") and r.get("kind", "object") == "object" for r in results
        )
        self.cheat_window.append(bool(has_cheat))

        if self.vai_tro != ROLE_FRONT:
            self.behavior_window.append(False)
            return

        n_persons, _ = _last_pose_info.get(self.ns, (0, 0.0))
        now = time.time()
        if n_persons > 0:
            self.last_seen_person = now
            self.vang_fired = False
        absent_long = n_persons == 0 and (now - self.last_seen_person) > ABSENT_SECONDS

        has_behavior = any(r.get("kind") == "behavior" for r in results)
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
                if self.vai_tro != ROLE_FRONT:
                    continue
                if r.get("label") == "quay_sau":
                    kept.append(r)
                elif _window_ok(self.behavior_window):
                    kept.append(r)
                continue
            if _window_ok(self.cheat_window):
                kept.append(r)

        if self.vai_tro == ROLE_FRONT:
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

        _save_snapshot(
            db,
            self.session_id,
            annotated,
            kept,
            image_dir,
            self.frame_count,
            vai_tro_camera=self.vai_tro,
        )

    def _other_streams_active(self) -> bool:
        now = time.time()
        with _workers_lock:
            for (sid, role), worker in _workers.items():
                if (
                    sid == self.session_id
                    and role != self.vai_tro
                    and worker.running
                    and now - worker.last_activity <= IDLE_STOP_SECONDS
                ):
                    return True
        return False

    def _mark_stream_status(self, status: str) -> None:
        from models.camera_stream import CameraStream

        db = SessionLocal()
        try:
            stream = (
                db.query(CameraStream)
                .filter(
                    CameraStream.FK_MaPhienGiamSat == self.session_id,
                    CameraStream.VaiTro == self.vai_tro,
                )
                .first()
            )
            if stream is not None:
                stream.TrangThai = status
                db.commit()
        except Exception as exc:
            db.rollback()
            logger.debug(f"Mark stream status failed: {exc}")
        finally:
            db.close()

    def _should_stop(self, db) -> bool:
        """Dừng worker khi phiên kết thúc hoặc luồng này quá lâu không có frame.

        Với 2 camera: một luồng mất kết nối chỉ đánh dấu luồng đó, không kết thúc
        phiên nếu luồng còn lại vẫn đang gửi frame.
        """
        if time.time() - self.last_activity > IDLE_STOP_SECONDS:
            self.running = False
            self._mark_stream_status("mat_ket_noi")
            if not self._other_streams_active():
                try:
                    end_session(db, self.session_id)
                except Exception as exc:
                    logger.debug(
                        f"End session #{self.session_id} on idle timeout failed: {exc}"
                    )
            return True
        try:
            s = get_session_by_id(db, self.session_id)
            if s is None or s.TrangThai != "dang_giam_sat":
                self.running = False
                return True
        except Exception:
            pass
        return False


def ensure_worker(session_id: int, vai_tro: str = ROLE_FRONT) -> "_SessionWorker":
    """Lấy hoặc tạo worker cho luồng camera (an toàn luồng)."""
    role = _normalize_role(vai_tro)
    key = (session_id, role)
    with _workers_lock:
        worker = _workers.get(key)
        if worker is None or not worker.running:
            worker = _SessionWorker(session_id, role)
            _workers[key] = worker
        return worker


def ingest_frame(
    session_id: int,
    token: str,
    ts_client: float,
    jpg: bytes,
    vai_tro: str = ROLE_FRONT,
) -> tuple[bool, str]:
    """Nhận frame từ browser: check token/role, skew, định dạng rồi xếp hàng.
    Trả về (ok, lý do)."""
    role = _normalize_role(vai_tro)
    resolved = resolve_token(token)
    if resolved != (session_id, role):
        return False, TOKEN_INVALID
    if abs(time.time() - ts_client) > TS_SKEW_SECONDS:
        return False, "timestamp lệch quá 60s (nghi replay)"
    if not jpg or len(jpg) > MAX_JPG_BYTES:
        return False, "kích thước ảnh không hợp lệ"
    if len(jpg) < 3 or jpg[0] != 0xFF or jpg[1] != 0xD8 or jpg[2] != 0xFF:
        return False, "không phải JPEG"
    worker = ensure_worker(session_id, role)
    if not worker.push(jpg):
        return False, "hàng đợi bận"
    return True, "queued"


def stop_session_workers(session_id: int) -> None:
    """Dừng mọi worker của phiên + thu hồi token + reset tracker từng luồng."""
    with _workers_lock:
        keys = [key for key in _workers if key[0] == session_id]
        workers = [_workers[key] for key in keys]
    for worker in workers:
        worker.running = False
    revoke_session_tokens(session_id)
    for role in VALID_ROLES:
        ai_pipeline.reset_tracker(f"ingest-{session_id}-{role}")


def get_latest_frame(session_id: int, vai_tro: str | None = None) -> bytes | None:
    """Lấy frame JPEG đã qua AI mới nhất của một luồng (hoặc ưu tiên camera trước)."""
    roles = [vai_tro] if vai_tro in VALID_ROLES else [ROLE_FRONT, ROLE_SIDE]
    with _workers_lock:
        for role in roles:
            worker = _workers.get((session_id, role))
            if worker and worker.latest_jpeg:
                return worker.latest_jpeg
    return None


def get_stream_activity(session_id: int, stale_seconds: float = 60.0) -> dict[str, bool]:
    """Trạng thái hoạt động từng luồng camera (dùng cho lưới giám thị)."""
    now = time.time()
    result = {ROLE_FRONT: False, ROLE_SIDE: False}
    with _workers_lock:
        for (sid, role), worker in _workers.items():
            if sid != session_id:
                continue
            result[role] = bool(
                worker.running and (now - worker.last_activity <= stale_seconds)
            )
    return result


def is_session_active(session_id: int, stale_seconds: float = 60.0) -> bool:
    """True nếu có ít nhất một luồng camera còn gửi frame gần đây."""
    return any(get_stream_activity(session_id, stale_seconds).values())
