"""Vòng đời camera: mở, dừng, liệt kê thiết bị và video mẫu.
Luồng chính: tạo phiên gắn thiết bị biên → mở RTSP/camera/video file → chạy capture loop nền."""

import threading
from pathlib import Path

import cv2

from core.exceptions import NotFoundError, ValidationError
from core.logger import get_logger
from crud.device_crud import get_device_by_id, update_device
from crud.session_crud import create_session, end_session
from database.database import SessionLocal
from schemas.device import DeviceUpdate
from service.camera_state import CameraState
from service.pipeline_service import capture_loop

logger = get_logger(__name__)


def _open_rtsp_source(rtsp: str, state: CameraState) -> None:
    """Mở nguồn RTSP: index webcam số, file video, hoặc URL rtsp/http."""
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

    state.cap = cv2.VideoCapture(rtsp, cv2.CAP_ANY)
    state.source = rtsp
    state.loop_video = False


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

    session = create_session(
        db=db,
        user_id=user_id,
        device_id=device_id,
        phong_thi=phong_thi,
        mon_thi=mon_thi,
    )
    state.current_session_id = session.PK_MaPhienGiamSat
    state.device_id = device_id
    device_name = device.TenThietBi
    device_rtsp = device.DuongDanRTSP
    db.close()

    _open_rtsp_source(video_path or device_rtsp, state)

    if not state.cap or not state.cap.isOpened():
        raise RuntimeError(f"Cannot open source for device {device_name}")

    state.running = True
    update_device_status(device_id, "dang_chay")

    state.thread = threading.Thread(target=capture_loop, daemon=True)
    state.thread.start()

    logger.info(f"Device {device_name} started — session {state.current_session_id}")
    return state.current_session_id


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
