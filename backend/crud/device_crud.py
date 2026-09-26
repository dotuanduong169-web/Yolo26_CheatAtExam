"""Quản lý thiết bị biên trong DB.
Logic chính: xóa thiết bị đang có phiên thì chặn (RESTRICT ở DB).
"""

from typing import Optional

from sqlalchemy.orm import Session as DBSession

from models.edgedevice import EdgeDevice
from schemas.device import DeviceCreate, DeviceUpdate


def create_device(db: DBSession, data: DeviceCreate) -> EdgeDevice:
    """Đăng ký thiết bị biên mới."""
    device = EdgeDevice(
        TenThietBi=data.TenThietBi,
        DuongDanRTSP=data.DuongDanRTSP,
        MoTaViTri=data.MoTaViTri,
    )
    db.add(device)
    db.commit()
    db.refresh(device)
    return device


def get_device_by_id(db: DBSession, device_id: int) -> Optional[EdgeDevice]:
    """Tìm thiết bị theo khóa chính."""
    return db.query(EdgeDevice).filter(EdgeDevice.PK_MaThietBi == device_id).first()


def list_devices(db: DBSession, skip: int = 0, limit: int = 50) -> list[EdgeDevice]:
    """Liệt kê thiết bị, mới nhất trước."""
    return (
        db.query(EdgeDevice)
        .order_by(EdgeDevice.PK_MaThietBi.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def update_device(db: DBSession, device_id: int, data: DeviceUpdate) -> Optional[EdgeDevice]:
    """Sửa thiết bị, field None thì giữ nguyên."""
    device = get_device_by_id(db, device_id)
    if not device:
        return None

    if data.TenThietBi is not None:
        device.TenThietBi = data.TenThietBi
    if data.DuongDanRTSP is not None:
        device.DuongDanRTSP = data.DuongDanRTSP
    if data.MoTaViTri is not None:
        device.MoTaViTri = data.MoTaViTri
    if data.TrangThai is not None:
        device.TrangThai = data.TrangThai
    db.commit()
    db.refresh(device)
    return device


def delete_device(db: DBSession, device_id: int) -> bool:
    """Xóa thiết bị. Trả False nếu không tồn tại; DB chặn khi còn phiên liên quan."""
    device = get_device_by_id(db, device_id)
    if not device:
        return False

    db.delete(device)
    db.commit()
    return True
