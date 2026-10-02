"""Endpoint thiết bị biên cho đăng ký camera/đầu ghi RTSP.
Logic chính: admin quản lý thiết bị; user thường chỉ xem để chọn nguồn giám sát.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.dependencies import get_current_user
from core.exceptions import AuthorizationError, NotFoundError
from core.logger import get_logger
from database.database import get_db
from models.user import User
from schemas.common import MessageResponse
from schemas.device import DeviceCreate, DeviceResponse, DeviceUpdate
from crud.device_crud import (
    create_device,
    delete_device,
    get_device_by_id,
    list_devices,
    update_device,
)

logger = get_logger(__name__)
router = APIRouter(prefix="/devices", tags=["Devices"])


def _require_admin(user: User) -> None:
    """Chặn user thường khỏi endpoint quản trị."""
    if user.VaiTro != "admin":
        raise AuthorizationError(detail="Admin only")


@router.post("", response_model=DeviceResponse)
def register_device(
    data: DeviceCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Đăng ký thiết bị biên mới. Chỉ admin."""
    _require_admin(user)
    return create_device(db, data)


@router.get("", response_model=list[DeviceResponse])
def get_devices(
    skip: int = 0,
    limit: int = 50,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Liệt kê thiết bị biên. Mọi user đăng nhập đều xem được để chọn nguồn."""
    return list_devices(db, skip, limit)


@router.get("/{device_id}", response_model=DeviceResponse)
def get_device(
    device_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lấy một thiết bị theo ID."""
    device = get_device_by_id(db, device_id)
    if not device:
        raise NotFoundError(detail="Device not found")
    return device


@router.put("/{device_id}", response_model=DeviceResponse)
def update_device_endpoint(
    device_id: int,
    data: DeviceUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Sửa thiết bị. Chỉ admin."""
    _require_admin(user)
    device = update_device(db, device_id, data)
    if not device:
        raise NotFoundError(detail="Device not found")
    return device


@router.delete("/{device_id}", response_model=MessageResponse)
def delete_device_endpoint(
    device_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Xóa thiết bị. Chỉ admin; DB chặn khi còn phiên liên quan."""
    _require_admin(user)
    try:
        if not delete_device(db, device_id):
            raise NotFoundError(detail="Device not found")
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Không thể xóa thiết bị đang gắn ca thi hoặc có phiên giám sát")
    return {"message": "Xóa thiết bị thành công"}


@router.post("/{device_id}/test")
def test_device_endpoint(
    device_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Kiểm tra kết nối thực tế tới camera của thiết bị biên."""
    device = get_device_by_id(db, device_id)
    if not device:
        raise NotFoundError(detail="Không tìm thấy thiết bị")
    from service.camera_service import test_camera_connection
    return test_camera_connection(device.DuongDanRTSP)


# ── AI Configuration Endpoints ──────────────────────────────
import json
from pathlib import Path
from pydantic import BaseModel

AI_CONFIG_FILE = Path(__file__).resolve().parents[2] / "ai_config.json"

class AIConfigPayload(BaseModel):
    conf_thresh: float
    time_thresh: float

@router.get("/ai-config/get")
def get_ai_config(user: User = Depends(get_current_user)):
    """Lấy cấu hình tham số AI nhận diện hiện tại."""
    if AI_CONFIG_FILE.exists():
        try:
            with open(AI_CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"conf_thresh": 0.75, "time_thresh": 2.5}

@router.post("/ai-config/save")
def save_ai_config(payload: AIConfigPayload, user: User = Depends(get_current_user)):
    """Lưu cấu hình tham số AI nhận diện."""
    _require_admin(user)
    data = {"conf_thresh": round(payload.conf_thresh, 2), "time_thresh": round(payload.time_thresh, 1)}
    try:
        with open(AI_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        # Cập nhật runtime nếu có
        try:
            import ai_model.ai_pipeline as aip
            aip.CONF_THRESHOLD = data["conf_thresh"]
        except Exception:
            pass
        return {"message": "Cấu hình AI đã được lưu thành công", "config": data}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Không thể lưu cấu hình: {exc}")

