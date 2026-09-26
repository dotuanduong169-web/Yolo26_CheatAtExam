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
        raise HTTPException(status_code=400, detail="Device has monitoring sessions")
    return {"message": "Device deleted successfully"}
