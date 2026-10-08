"""Vòng đời camera: mở, dừng, liệt kê thiết bị và video mẫu.
Luồng chính: tạo phiên gắn thiết bị biên → mở RTSP/camera/video file → chạy capture loop nền."""

import os
import socket
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import cv2

from core.exceptions import NotFoundError, ValidationError
from core.logger import get_logger
from crud.device_crud import get_device_by_id, update_device
from crud.session_crud import create_session, end_session
from database.database import SessionLocal
from models.monitoring_session import MonitoringSession
from schemas.device import DeviceUpdate
from service.camera_state import CameraState
from service.pipeline_service import capture_loop

logger = get_logger(__name__)


def is_rtsp_reachable(rtsp_url: str, timeout: float = 2.0) -> bool:
    """Kiểm tra cổng TCP của nguồn RTSP trước khi mở, tránh treo request 30-90s."""
    if not (rtsp_url.startswith("rtsp://") or rtsp_url.startswith("http://") or rtsp_url.startswith("https://")):
        return True
    try:
        parsed = urlparse(rtsp_url)
        host = parsed.hostname
        if not host:
            return True
        port = parsed.port or (554 if rtsp_url.startswith("rtsp://") else 80)
        sock = socket.create_connection((host, port), timeout=timeout)
        sock.close()
        return True
    except (socket.timeout, socket.error, OSError) as exc:
        logger.warning(f"RTSP host unreachable ({rtsp_url}): {exc}")
        return False


def _open_rtsp_source(rtsp: str, state: CameraState) -> None:
    """Mở nguồn RTSP: index webcam số, file video, hoặc URL rtsp/http có timeout ngắn."""
    # Cài đặt timeout ngắn cho FFmpeg backend của OpenCV (2.5 giây thay vì treo 30-90s)
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "timeout;2500000|stimeout;2500000"

    if rtsp.isdigit():
        state.cap = cv2.VideoCapture(int(rtsp), cv2.CAP_ANY)
        try:
            state.cap.set(cv2.CAP_PROP_FPS, 15)
        except Exception:
            pass
        state.source = f"camera_{rtsp}"
        state.loop_video = False
        return

    path = Path(rtsp)
    if not path.is_absolute():
        from core.config import settings as _s
        path = (_s.PROJECT_ROOT / rtsp).resolve()
    if path.exists():
        state.cap = cv2.VideoCapture(str(path))
        state.source = str(path)
        state.loop_video = True
        return

    # Kiểm tra mạng nhanh cho luồng mạng
    if not is_rtsp_reachable(rtsp, timeout=2.0):
        logger.error(f"Cannot connect to RTSP endpoint: {rtsp}")
        state.cap = None
        state.source = rtsp
        state.loop_video = False
        return

    state.cap = cv2.VideoCapture(rtsp, cv2.CAP_ANY)
    state.source = rtsp
    state.loop_video = False


def cleanup_orphan_sessions(db=None) -> int:
    """Dọn dẹp các phiên mồ côi đang treo trạng thái dang_giam_sat mà camera không chạy."""
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True
    try:
        state = CameraState()
        active_id = state.current_session_id if state.is_running() else None
        query = db.query(MonitoringSession).filter(
            MonitoringSession.TrangThai == "dang_giam_sat",
            MonitoringSession.FK_MaThiSinh.is_(None),
            MonitoringSession.FK_MaThietBi.isnot(None),
        )
        if active_id:
            query = query.filter(MonitoringSession.PK_MaPhienGiamSat != active_id)

        orphans = query.all()
        now_utc = datetime.now(timezone.utc)
        count = len(orphans)
        for s in orphans:
            s.TrangThai = "ket_thuc"
            if not s.ThoiGianKetThuc:
                s.ThoiGianKetThuc = now_utc
        if count > 0:
            db.commit()
            logger.info(f"Cleaned up {count} orphan monitoring sessions")
        return count
    except Exception as exc:
        db.rollback()
        logger.warning(f"Failed to cleanup orphan sessions: {exc}")
        return 0
    finally:
        if close_db:
            db.close()


def test_camera_connection(rtsp: str) -> dict:
    """Kiểm tra kết nối thực tế tới camera/RTSP và đo độ trễ thực tế."""
    start_t = time.time()
    if rtsp.isdigit():
        cap = cv2.VideoCapture(int(rtsp), cv2.CAP_ANY)
        if cap.isOpened():
            ret, _ = cap.read()
            cap.release()
            latency = int((time.time() - start_t) * 1000)
            if ret:
                return {"online": True, "latency_ms": max(latency, 2), "message": "Kết nối thành công (Camera máy chủ)"}
        return {"online": False, "latency_ms": 0, "message": "Không thể mở webcam hoặc thiết bị bị chiếm dụng"}

    path = Path(rtsp)
    if not path.is_absolute():
        from core.config import settings as _s
        path = (_s.PROJECT_ROOT / rtsp).resolve()
    if path.exists():
        return {"online": True, "latency_ms": 2, "message": f"Tệp video mẫu sẵn sàng ({path.name})"}

    if not is_rtsp_reachable(rtsp, timeout=2.0):
        return {"online": False, "latency_ms": 0, "message": "Không thể kết nối đến địa chỉ RTSP (Camera ngoại tuyến hoặc sai IP/cổng)"}

    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "timeout;2000000|stimeout;2000000"
    cap = cv2.VideoCapture(rtsp, cv2.CAP_ANY)
    if cap and cap.isOpened():
        ret, _ = cap.read()
        cap.release()
        latency = int((time.time() - start_t) * 1000)
        if ret:
            return {"online": True, "latency_ms": max(latency, 5), "message": f"Luồng RTSP ổn định ({latency}ms)"}
    return {"online": False, "latency_ms": 0, "message": "Không nhận được luồng hình ảnh từ camera RTSP"}


def start_camera(
    user_id: int,
    device_id: int,
    phong_thi: str | None = None,
    mon_thi: str | None = None,
    video_path: str | None = None,
) -> int:
    """
    Mở thiết bị biên rồi chạy capture loop nền.
    Điểm logic: video_path (test offline) đè lên RTSP của thiết bị;
    đang chạy thì trả luôn phiên hiện tại; thiết bị khóa thì từ chối.

    Raises:
        NotFoundError: Thiết bị không tồn tại.
        ValidationError: Thiết bị đang khóa.
        RuntimeError: Không mở được nguồn hình.
    """
    state = CameraState()

    if state.is_running():
        return state.current_session_id

    db = SessionLocal()
    device = get_device_by_id(db, device_id)
    if not device:
        db.close()
        raise NotFoundError(detail="Device not found")
    if device.TrangThai == "tat":
        db.close()
        raise ValidationError(detail="Device is disabled")

    device_name = device.TenThietBi
    device_rtsp = device.DuongDanRTSP
    target_source = video_path or device_rtsp

    # Kiểm tra khả năng mở luồng trước hoặc tạo session có khối bảo vệ dọn dẹp
    session = create_session(
        db=db,
        user_id=user_id,
        device_id=device_id,
        phong_thi=phong_thi,
        mon_thi=mon_thi,
    )
    session_id = session.PK_MaPhienGiamSat
    state.current_session_id = session_id
    state.device_id = device_id
    db.close()

    try:
        _open_rtsp_source(target_source, state)

        if not state.cap or not state.cap.isOpened():
            raise RuntimeError(f"Không thể mở nguồn hình cho thiết bị {device_name} ({target_source})")

        # Đọc thử 1 frame để kiểm tra luồng thực tế
        ret, _ = state.cap.read()
        if not ret:
            raise RuntimeError(f"Không đọc được khung hình từ {device_name}")

        try:
            # Buffer 1 frame: luôn đọc frame mới nhất, box bám vật thể đang di chuyển
            state.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        except Exception:
            pass

        state.running = True
        state.start_time = time.time()
        update_device_status(device_id, "dang_chay")

        state.thread = threading.Thread(target=capture_loop, daemon=True)
        state.thread.start()

        logger.info(f"Device {device_name} started — session {state.current_session_id}")
        return state.current_session_id

    except Exception as exc:
        # Xử lý dọn dẹp phiên mồ côi: đánh dấu kết thúc phiên vừa tạo nếu mở luồng thất bại
        logger.error(f"start_camera failed, cleaning up session #{session_id}: {exc}")
        if state.cap:
            try:
                state.cap.release()
            except Exception:
                pass
            state.cap = None

        db_cleanup = SessionLocal()
        try:
            end_session(db_cleanup, session_id)
        finally:
            db_cleanup.close()

        state.reset()
        raise RuntimeError(f"Không thể kết nối camera {device_name}: {exc}")



def update_device_status(device_id: int, trang_thai: str) -> None:
    """Đổi trạng thái thiết bị, bỏ qua lỗi để không chặn luồng capture."""
    try:
        db = SessionLocal()
        update_device(db, device_id, DeviceUpdate(TrangThai=trang_thai))
        db.close()
    except Exception as exc:
        logger.debug(f"Update device status failed: {exc}")


def stop_camera() -> None:
    """Dừng camera đang chạy và chốt phiên.
    Điểm logic: nhả thiết bị trước rồi mới đóng phiên để không kẹt tài nguyên."""
    state = CameraState()
    state.running = False

    if state.cap:
        state.cap.release()
        state.cap = None

    db = SessionLocal()
    if state.current_session_id:
        end_session(db, state.current_session_id)
    device_id = state.device_id
    db.close()

    if device_id is not None:
        update_device_status(device_id, "san_sang")

    state.reset()
    logger.info("Camera stopped")


def list_cameras(max_index: int = 5) -> list[int]:
    """Dò các cổng camera còn đọc được hình, tương thích nhiều hệ điều hành.
    Điểm logic: chỉ nhận cổng mở được và đọc thử thành công một frame."""
    available: list[int] = []
    for i in range(max_index):
        cap = cv2.VideoCapture(i, cv2.CAP_ANY)
        if cap.isOpened():
            ret, _ = cap.read()
            if ret:
                available.append(i)
        cap.release()
    return available


def list_camera_with_name() -> list[dict]:
    """Liệt kê camera live kèm video mẫu trong thư mục videos.
    Điểm logic: video mẫu gắn cổng -1 để phân biệt với camera live."""
    cameras = [{"index": i, "name": f"Camera {i}"} for i in list_cameras()]
    try:
        from core.config import settings as _s
        videos_dir = _s.PROJECT_ROOT / "videos"
        if videos_dir.exists():
            for f in sorted(videos_dir.glob("*.mp4")):
                cameras.append({"index": -1, "name": f"video:{f.name}"})
    except Exception:
        pass
    return cameras
