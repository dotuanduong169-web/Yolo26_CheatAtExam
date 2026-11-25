"""Ingest frame thi online: hàng đợi + worker infer riêng cho từng luồng camera.

Mỗi phiên con có thể có 2 luồng:
- front: webcam máy tính (pose + object + vắng mặt/nhiều người)
- side : điện thoại đặt sau/bên (chỉ object detection)

Luồng chính: browser POST frame (kèm vai_tro) -> xác thực token theo stream ->
queue giữ frame mới nhất -> worker infer -> debounce -> snapshot bằng chứng +
snapshot nền (raw -> normalized -> tbl_snapshot/tbl_snapshot_processed).
"""

import os
import secrets
import threading
import time
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
from service.camera_state import OBJECT_COOLDOWN_SECONDS, POSE_COOLDOWN_SECONDS
from service.pipeline_service import SAVE_INTERVAL_SECONDS, _save_event_snapshot
from service.timeline_service import record_tick

logger = get_logger(__name__)

# Giới hạn ingest chống spam/dồn khi mạng về
MAX_JPG_BYTES = 500 * 1024
QUEUE_MAXLEN = 3
TS_SKEW_SECONDS = 60
# Vắng mặt: không thấy người liên tục quá ngưỡng này (giây) mới cảnh báo.
# 6 giây ~ 2-3 tick 2,5 giây, đủ tránh báo oan khi thí sinh cúi lấy bút.
ABSENT_SECONDS = max(3.0, float(os.getenv("ABSENT_SECONDS", "6")))
# Camera bị che/tối: ảnh gần như đồng màu, mất chi tiết. Che tay vào lens
# thường không làm pose trả n_persons = 0 ngay, nên cần tín hiệu ảnh độc lập.
OBSTRUCTED_SECONDS = max(2.0, float(os.getenv("OBSTRUCTED_SECONDS", "4")))
ABSENT_DARK_MEAN = float(os.getenv("ABSENT_DARK_MEAN", "22"))
ABSENT_FLAT_STD = float(os.getenv("ABSENT_FLAT_STD", "8"))
ABSENT_FLAT_LAPLACIAN = float(os.getenv("ABSENT_FLAT_LAPLACIAN", "15"))
# Hành vi tư thế phải xuất hiện ở 2 tick liên tiếp mới lưu (giảm báo sai do
# keypoint nhiễu/ánh sáng). quay_sau, vang_mat, nhieu_nguoi vẫn kích hoạt ngay.
POSE_CONFIRM_TICKS = max(1, int(os.getenv("POSE_CONFIRM_TICKS", "2")))
# Một nhãn biến mất 1 tick (nhận diện chập chờn) chưa mở lại cảnh báo; phải
# vắng đủ số tick này mới coi là kết thúc đợt và cho phép cảnh báo lại.
ALERT_CLEAR_TICKS = max(1, int(os.getenv("ALERT_CLEAR_TICKS", "2")))
POSE_LABELS = {"quay_dau", "quay_sau", "cui_xuong"}
IDLE_STOP_SECONDS = 120

ROLE_FRONT = "front"
ROLE_SIDE = "side"
VALID_ROLES = {ROLE_FRONT, ROLE_SIDE}
ROLE_LABELS = {ROLE_FRONT: "Camera trước", ROLE_SIDE: "Camera phụ"}

# Nhật ký tick: mặc định bật. Ghi mọi tick có cảnh báo, tick đổi trạng thái và
# heartbeat khi sạch. 2,5 giây chỉ là nhịp tham khảo từ trình duyệt; hệ thống ghi
# theo tick thực tế nhận được, không phụ thuộc cứng vào 2,5 giây.
TIMELINE_ENABLED = os.getenv("TIMELINE_ENABLED", "1") != "0"
TIMELINE_HEARTBEAT_SECONDS = max(5.0, float(os.getenv("TIMELINE_HEARTBEAT_SECONDS", "30")))

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


def frame_obstructed(frame: np.ndarray) -> bool:
    """True khi ảnh gần như không dùng được: quá tối, quá phẳng hoặc mất chi tiết.

    Dùng để bắt trường hợp thí sinh lấy tay che camera: pose vẫn có thể trả về
    một "người" mờ nên chỉ dựa vào n_persons == 0 sẽ không cảnh báo được.
    """
    if frame is None or getattr(frame, "size", 0) == 0:
        return True
    try:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        small = cv2.resize(gray, (64, 48), interpolation=cv2.INTER_AREA)
        mean = float(small.mean())
        std = float(small.std())
        if mean < ABSENT_DARK_MEAN:
            return True
        lap_var = float(cv2.Laplacian(small, cv2.CV_64F).var())
        # Gần như đồng màu (std rất thấp) hoặc mất cạnh do mất nét: tay/bàn tay
        # áp sát lens, vật che kín, hoặc ảnh không còn chi tiết dùng được.
        return std < ABSENT_FLAT_STD or lap_var < ABSENT_FLAT_LAPLACIAN
    except Exception:
        return False


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


def _encode_live_thumb(frame: np.ndarray) -> bytes | None:
    """Thumbnail nhẹ cho lưới giám thị, encode đúng một lần mỗi tick.

    Dùng cùng kích thước/chất lượng với thumbnail timeline để payload tương đương
    (~15-20 KB), nhưng KHÔNG ghi DB/đĩa: ảnh nằm trong RAM và tươi theo từng
    khung 2,5 giây thay vì chờ heartbeat 30 giây.
    """
    try:
        if frame is None or getattr(frame, "size", 0) == 0:
            return None
        img = frame
        max_w = snapshot_service.TIMELINE_IMAGE_MAX_WIDTH
        if img.shape[1] > max_w:
            ratio = max_w / float(img.shape[1])
            img = cv2.resize(
                img,
                (max_w, max(1, int(img.shape[0] * ratio))),
                interpolation=cv2.INTER_AREA,
            )
        ok, buf = cv2.imencode(
            ".jpg",
            img,
            [cv2.IMWRITE_JPEG_QUALITY, snapshot_service.TIMELINE_JPEG_QUALITY],
        )
        return buf.tobytes() if ok else None
    except Exception:
        return None


class _SessionWorker:
    """Worker infer cho một luồng camera (session_id, vai_tro)."""

    def __init__(self, session_id: int, vai_tro: str = ROLE_FRONT):
        self.session_id = session_id
        self.vai_tro = _normalize_role(vai_tro)
        self.ns = f"ingest-{session_id}-{self.vai_tro}"
        self.queue: Queue = Queue(maxsize=QUEUE_MAXLEN)
        self.frame_count = 0
        self.last_save = 0.0
        # Cooldown RIÊNG theo từng nhãn: một cellphone không được chặn Cheat_Paper,
        # một quay_dau không được chặn cui_xuong.
        self.last_save_by_label: dict[str, float] = {}
        self.last_snapshot_save = 0.0
        self.last_seen_person = time.time()
        self.vang_fired = False
        self.multi_fired = False
        self.single_streak = 0
        self.occluded_since = 0.0
        # Số tick liên tiếp thấy mỗi nhãn hành vi (xác nhận chống báo sai).
        self.pose_streak: dict[str, int] = {}
        # Nhãn đang trong một "đợt" đã cảnh báo: không lưu lặp mỗi cooldown khi
        # điện thoại vẫn nằm trên bàn / đầu vẫn quay. Chỉ mở lại khi nhãn biến mất.
        self.active_alerts: set[str] = set()
        self.alert_misses: dict[str, int] = {}
        self.last_activity = time.time()
        self.latest_jpeg: bytes | None = None
        # Thumbnail nhẹ cho lưới giám thị, encode 1 lần mỗi tick và giữ trong RAM.
        # Không ghi DB/đĩa nên ảnh lưới tươi theo đúng nhịp 2,5 giây.
        self.latest_thumb: bytes | None = None
        self.tick_index = 0
        self.last_timeline_signature = None
        self.last_timeline_write = 0.0
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    @staticmethod
    def _cooldown_for(label: str) -> float:
        """Cooldown theo loại: vật thể 15s, hành vi tư thế/vắng mặt 6s."""
        if label in {"Cheat_Paper", "cellphone"}:
            return OBJECT_COOLDOWN_SECONDS
        return POSE_COOLDOWN_SECONDS

    def _note_pose_streak(self, cheat_results: list[dict]) -> None:
        """Đếm số tick liên tiếp thấy từng nhãn tư thế; mất 1 tick thì reset."""
        labels = {
            str(r.get("label") or "")
            for r in cheat_results
            if r.get("kind") == "behavior" and r.get("label") in POSE_LABELS
        }
        for label in list(self.pose_streak):
            if label not in labels:
                self.pose_streak.pop(label, None)
        for label in labels:
            self.pose_streak[label] = min(self.pose_streak.get(label, 0) + 1, 10)

    def _update_alert_episodes(self, cheat_results: list[dict]) -> None:
        """Đóng/mở đợt cảnh báo theo việc nhãn còn xuất hiện hay không."""
        present = {str(r.get("label") or "") for r in cheat_results}
        for label in list(self.active_alerts):
            if label in present:
                self.alert_misses[label] = 0
                continue
            misses = self.alert_misses.get(label, 0) + 1
            self.alert_misses[label] = misses
            if misses >= ALERT_CLEAR_TICKS:
                self.active_alerts.discard(label)
                self.alert_misses.pop(label, None)

    def _label_ready(self, r: dict, now: float) -> bool:
        """Nhãn đã đủ xác nhận, chưa cảnh báo trong đợt này và hết cooldown chưa."""
        label = str(r.get("label") or "")
        if label in self.active_alerts:
            return False
        if r.get("kind") == "behavior" and label in POSE_LABELS:
            if label != "quay_sau" and self.pose_streak.get(label, 0) < POSE_CONFIRM_TICKS:
                return False
        # vang_mat/nhieu_nguoi đã tự chặn theo "đợt" bằng vang_fired/multi_fired,
        # nên bỏ qua cooldown để không mất cảnh báo khi thí sinh vừa ló mặt rồi
        # che camera lại trong vòng 6 giây.
        if label in {"vang_mat", "nhieu_nguoi"}:
            return True
        return now - self.last_save_by_label.get(label, 0.0) >= self._cooldown_for(label)

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
                    jpg, recv_ts = self.queue.get(timeout=1.0)
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
                    self.tick_index += 1
                    now = time.time()
                    if self.frame_count == 1:
                        self.last_seen_person = now
                        self.last_save = now
                        self.vang_fired = False

                    captured_at = datetime.fromtimestamp(recv_ts, tz=timezone.utc)
                    occluded = frame_obstructed(frame)
                    if occluded and self.vai_tro == ROLE_FRONT:
                        # Ảnh camera trước bị che/tối: bỏ luôn inference để tiết kiệm
                        # CPU và không sinh quay_dau/cellphone giả trước khi báo
                        # vang_mat. Camera phụ vẫn giữ object detection.
                        annotated, results = frame, []
                    else:
                        annotated, results = process_frame(
                            frame,
                            self.frame_count,
                            tracker_ns=self.ns,
                            enable_pose=(self.vai_tro == ROLE_FRONT),
                            force_infer=True,
                        )
                    ok, buf = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 75])
                    if ok:
                        self.latest_jpeg = buf.tobytes()
                    self.latest_thumb = _encode_live_thumb(annotated)
                    self._note_windows(results, occluded=occluded)

                    now = time.time()
                    cheat_results = [r for r in results if r.get("is_cheat")]
                    self._note_pose_streak(cheat_results)
                    self._update_alert_episodes(cheat_results)

                    # Chỉ lưu sự kiện cho nhãn đã đủ xác nhận + hết cooldown riêng.
                    # Không dùng danh sách "tất cả cheat" ở đây: nhãn đang trong
                    # cooldown/chưa xác nhận sẽ bị lưu lặp mỗi chu kỳ.
                    due_results = [r for r in cheat_results if self._label_ready(r, now)]
                    saved_event_ids: list[int] = []
                    if due_results:
                        saved_event_ids = self._snapshot(
                            db, annotated, due_results, image_dir
                        ) or []
                        if saved_event_ids:
                            # Chỉ đánh dấu cooldown/đợt khi ghi DB thành công;
                            # lỗi tạm thời sẽ được thử lại ở tick sau.
                            for label in {str(r.get("label") or "") for r in due_results}:
                                self.last_save_by_label[label] = now
                                self.active_alerts.add(label)
                                self.alert_misses[label] = 0
                            self.last_save = now
                    elif now - self.last_save > SAVE_INTERVAL_SECONDS:
                        # Snapshot nền định kỳ KHÔNG tạo sự kiện. Trước đây nhánh
                        # này gọi _snapshot với mọi detection nên 10 giây lại nhân
                        # bản sự kiện đang cooldown (nguồn gốc cảnh báo lặp).
                        if not TIMELINE_ENABLED:
                            self._persist_snapshot(jpg, annotated)
                        self.last_save = now

                    # Nhật ký tick 2,5 giây (tham khảo): ghi mọi tick có cảnh báo,
                    # tick đổi trạng thái và heartbeat. Không ghi tick sạch lặp lại.
                    if TIMELINE_ENABLED:
                        signature = tuple(
                            sorted(
                                (
                                    str(r.get("label") or ""),
                                    round(float(r.get("confidence") or 0.0), 1),
                                    tuple(
                                        round(float(v), 0)
                                        for v in (r.get("bbox") or [])[:4]
                                    ),
                                )
                                for r in cheat_results
                            )
                        )
                        has_alert = bool(cheat_results)
                        state_changed = signature != self.last_timeline_signature
                        heartbeat_due = (
                            now - self.last_timeline_write
                        ) >= TIMELINE_HEARTBEAT_SECONDS
                        if has_alert or state_changed or heartbeat_due:
                            snapshot_id = snapshot_service.capture_timeline_snapshot(
                                self.session_id,
                                self.vai_tro,
                                annotated,
                                captured_at=captured_at,
                            )
                            record_tick(
                                session_id=self.session_id,
                                vai_tro=self.vai_tro,
                                tick_index=self.tick_index,
                                captured_at=captured_at,
                                results=results,
                                has_alert=has_alert,
                                snapshot_id=snapshot_id,
                                event_ids=saved_event_ids,
                                recv_ts=recv_ts,
                            )
                            self.last_timeline_signature = signature
                            self.last_timeline_write = now

                    # Khi timeline bật, thumbnail heartbeat đã phục vụ dashboard;
                    # không cần pipeline snapshot đầy đủ (raw/normalized) mỗi 30 giây.
                    if not TIMELINE_ENABLED and (
                        due_results
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

    def _note_windows(self, results: list[dict], occluded: bool = False) -> None:
        """Cập nhật debounce vật/hành vi + luật vắng mặt/nhiều người.

        Camera phụ chỉ chạy object detection nên không dùng cửa sổ behavior và
        không kích hoạt vang_mat/nhieu_nguoi (tránh báo trùng với camera trước).

        occluded=True khi ảnh tối/phẳng/mất chi tiết (tay che lens). Khi đó
        không tin n_persons do pose trả về và coi như không thấy thí sinh.
        """
        if self.vai_tro != ROLE_FRONT:
            return

        # None = chưa có kết quả pose lần nào (model chưa nạp hoặc lỗi suy luận):
        # không được coi là "0 người" rồi báo vắng mặt oan.
        pose_info = _last_pose_info.get(self.ns)
        pose_known = ai_pipeline.pose_available() and pose_info is not None
        n_persons, max_conf = pose_info if pose_info else (0, 0.0)
        now = time.time()

        if occluded:
            if self.occluded_since <= 0.0:
                self.occluded_since = now
        else:
            self.occluded_since = 0.0

        person_visible = (not occluded) and n_persons > 0
        if person_visible:
            self.last_seen_person = now
            self.vang_fired = False
        if not occluded and pose_known:
            if n_persons <= 1:
                self.single_streak += 1
                # Chỉ kết thúc đợt "nhiều người" khi thật sự còn 1 người ổn định,
                # tránh pose chập chờn 1 tick làm cảnh báo lặp lại.
                if self.single_streak >= ALERT_CLEAR_TICKS:
                    self.multi_fired = False
            else:
                self.single_streak = 0

        # Ân hạn khởi động: 3 frame đầu không cảnh báo để thí sinh ổn định.
        obstructed_long = (
            self.frame_count > 3
            and self.occluded_since > 0.0
            and (now - self.occluded_since) >= OBSTRUCTED_SECONDS
        )
        absent_long = (
            self.frame_count > 3
            and (occluded or pose_known)
            and not person_visible
            and (now - self.last_seen_person) > ABSENT_SECONDS
        )

        if (obstructed_long or absent_long) and not self.vang_fired:
            reason = "camera bị che/tối" if obstructed_long else "không thấy người"
            logger.info(
                f"[{self.session_id}/{self.vai_tro}] vang_mat: {reason} "
                f"(n_persons={n_persons}, occluded={occluded})"
            )
            results.append({
                "bbox": [],
                "mask": None,
                "label": "vang_mat",
                "confidence": 0.95 if obstructed_long else 0.9,
                "is_cheat": True,
                "kind": "behavior",
            })
            self.vang_fired = True

        # nhieu_nguoi: báo 1 lần mỗi đợt, chỉ reset khi trở lại đúng 1 người.
        if n_persons > 1 and not occluded and not self.multi_fired:
            logger.info(f"[{self.session_id}/{self.vai_tro}] nhieu_nguoi: n_persons={n_persons}")
            results.append({
                "bbox": [],
                "mask": None,
                "label": "nhieu_nguoi",
                "confidence": round(max_conf or 0.9, 4),
                "is_cheat": True,
                "kind": "behavior",
            })
            self.multi_fired = True

    def _snapshot(self, db, annotated, results, image_dir) -> list[int]:
        """Lưu đúng ảnh hiện tại + đúng các nhãn đã đủ điều kiện lưu.

        Không quét lại ``recent`` và không tự thêm vang_mat: việc quét lại từng
        lấy một ảnh cũ rồi lưu lại toàn bộ detection, tạo sự kiện trùng.
        """
        kept = [r for r in results if r.get("is_cheat")]
        if self.vai_tro != ROLE_FRONT:
            kept = [r for r in kept if r.get("kind") != "behavior"]
        if not kept:
            return []
        return _save_event_snapshot(
            db,
            self.session_id,
            annotated,
            kept,
            image_dir,
            self.frame_count,
            reason="ingest",
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


def get_latest_thumb(session_id: int, vai_tro: str | None = None) -> bytes | None:
    """Thumbnail live trong RAM của một luồng (cập nhật mỗi tick 2,5 giây)."""
    roles = [vai_tro] if vai_tro in VALID_ROLES else [ROLE_FRONT, ROLE_SIDE]
    with _workers_lock:
        for role in roles:
            worker = _workers.get((session_id, role))
            if worker and worker.latest_thumb:
                return worker.latest_thumb
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
