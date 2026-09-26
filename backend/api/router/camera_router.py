"""Endpoint camera cho mở luồng, dừng luồng và xem video trực tiếp.
Logic chính: mở theo thiết bị biên đã đăng ký; video_path test offline đè lên RTSP; mỗi lần mở tạo một phiên mới.
"""

import cv2
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from core.dependencies import get_current_user
from core.logger import get_logger
from database.database import get_db
from models.user import User
from schemas.camera import (
    CameraInfoResponse,
    CameraListResponse,
    CameraStartResponse,
    CameraStatusResponse,
    CameraStopResponse,
)
from service.camera_service import list_camera_with_name, start_camera, stop_camera
from service.camera_state import CameraState
from service.stream_service import gen_frames

logger = get_logger(__name__)
router = APIRouter(prefix="/camera", tags=["Camera"])


@router.get("/video_feed")
def video_feed():
    """Phát video trực tiếp. Trả luồng MJPEG multipart, lỗi thì báo 500."""
    try:
        return StreamingResponse(
            gen_frames(),
            media_type="multipart/x-mixed-replace; boundary=frame",
        )
    except Exception as exc:
        logger.error(f"Video stream error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to start video stream")


@router.post("/start", response_model=CameraStartResponse)
def start(
    device_id: int = Query(..., description="ID thiết bị biên đã đăng ký"),
    phong_thi: str | None = Query(None, max_length=50, description="Mã phòng thi"),
    mon_thi: str | None = Query(None, max_length=255, description="Tên môn thi"),
    video_path: str | None = Query(None, description="File video offline, VD: videos/test_exam.mp4"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mở thiết bị biên để giám sát. Tạo phiên mới gắn thiết bị, phòng/môn thi và user."""
    try:
        session_id = start_camera(
            user_id=user.PK_MaNguoiDung,
            device_id=device_id,
            phong_thi=phong_thi,
            mon_thi=mon_thi,
            video_path=video_path,
        )
        return {
            "message": f"Device {device_id} started",
            "session_id": session_id,
            "status": "running",
            "user_id": user.PK_MaNguoiDung,
        }
    except Exception as exc:
        logger.error(f"Failed to start camera: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to start camera: {exc}")


@router.post("/stop", response_model=CameraStopResponse)
def stop(user: User = Depends(get_current_user)):
    """Dừng camera đang chạy. Chốt phiên hiện tại để ghi giờ kết thúc."""
    try:
        stop_camera()
        return {"message": "Camera stopped", "status": "stopped", "user_id": user.PK_MaNguoiDung}
    except Exception as exc:
        logger.error(f"Failed to stop camera: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to stop camera: {exc}")


@router.get("/list", response_model=CameraListResponse)
def list_cam():
    """Liệt kê thiết bị camera. Đếm số lượng để client vẽ danh sách chọn nguồn."""
    try:
        cameras = list_camera_with_name()
        return {"cameras": cameras, "count": len(cameras)}
    except Exception as exc:
        logger.error(f"Failed to list cameras: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list cameras")


@router.get("/info", response_model=CameraInfoResponse)
def camera_info():
    """Lấy độ phân giải và trạng thái camera. Chưa mở camera thì trả mặc định 1280x720."""
    state = CameraState()
    if not state.cap:
        return {"width": 1280, "height": 720, "running": False}

    return {
        "width": int(state.cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        "height": int(state.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        "running": state.running,
    }


@router.get("/status", response_model=CameraStatusResponse)
def camera_status():
    """Lấy trạng thái camera hiện tại. Kèm session_id của phiên đang chạy nếu có."""
    state = CameraState()
    return {"running": state.running, "session_id": state.current_session_id}
