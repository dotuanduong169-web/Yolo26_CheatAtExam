"""Vòng đời camera: mở, dừng, liệt kê thiết bị và video mẫu.
Luồng chính: tạo ca thi → mở camera live hoặc video file → chạy capture loop nền."""

import threading
from pathlib import Path

import cv2

from crud.session_crud import create_session, end_session
from database.database import SessionLocal
from service.camera_state import CameraState
from service.pipeline_service import capture_loop
from core.logger import get_logger

logger = get_logger(__name__)


def start_camera(
    user_id: int = 1,
    class_id: str = "Unknown",
    camera_index: int = 0,
    video_path: str | None = None,
) -> int:
    """
    Mở camera live hoặc video file rồi chạy capture loop nền.
    Điểm logic: có video_path thì ưu tiên mở file và tự loop lại khi hết;
    không có thì mở camera live ở 15 FPS; đang chạy thì trả luôn ca hiện tại.

    Args:
        video_path: đường dẫn file video (ưu tiên nếu có) để chạy offline.
    """
    state = CameraState()

    if state.is_running():
        return state.current_session_id

    db = SessionLocal()
    source_label = video_path if video_path else f"camera_{camera_index}"
    session = create_session(
        db=db,
        user_id=user_id,
        class_id=class_id,
        camera_url=source_label,
    )
    state.current_session_id = session.session_id

    if video_path:
        path = Path(video_path)
        if not path.is_absolute():
            # Đường dẫn tương đối thì giải từ thư mục gốc dự án
            from core.config import settings as _s
            path = (_s.PROJECT_ROOT / video_path).resolve()
        if not path.exists():
            raise RuntimeError(f"Video file not found: {path}")
        state.cap = cv2.VideoCapture(str(path))
        state.source = str(path)
        state.loop_video = True
    else:
        # Camera live: dùng mã mở chung cho Linux và Windows, thử ưu tiên V4L2 trước.
        state.cap = cv2.VideoCapture(camera_index, cv2.CAP_ANY)
        state.cap.set(cv2.CAP_PROP_FPS, 15)
        state.source = f"camera_{camera_index}"
        state.loop_video = False

    if not state.cap.isOpened():
        raise RuntimeError(f"Cannot open source {source_label}")

    state.running = True

    state.thread = threading.Thread(target=capture_loop, daemon=True)
    state.thread.start()

    logger.info(f"Source {source_label} started — session {session.session_id}")
    return state.current_session_id


def stop_camera() -> None:
    """Dừng camera đang chạy và chốt ca thi.
    Điểm logic: nhả thiết bị trước rồi mới đóng ca để không kẹt tài nguyên."""
    state = CameraState()
    state.running = False

    if state.cap:
        state.cap.release()
        state.cap = None

    if state.current_session_id:
        db = SessionLocal()
        end_session(db, state.current_session_id)

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
