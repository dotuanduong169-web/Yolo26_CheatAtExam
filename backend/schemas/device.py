"""Schema thiết bị biên cho đăng ký camera/đầu ghi RTSP.
Logic chính: DuongDanRTSP là nguồn capture (index webcam hoặc rtsp://...).
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class DeviceCreate(BaseModel):
    """Dữ liệu đăng ký thiết bị mới."""

    TenThietBi: str = Field(..., min_length=1, max_length=255)
    DuongDanRTSP: str = Field(..., min_length=1, max_length=255)
    MoTaViTri: Optional[str] = Field(default=None, max_length=255)


class DeviceUpdate(BaseModel):
    """Dữ liệu sửa thiết bị, field nào None thì giữ nguyên."""

    TenThietBi: Optional[str] = Field(default=None, min_length=1, max_length=255)
    DuongDanRTSP: Optional[str] = Field(default=None, min_length=1, max_length=255)
    MoTaViTri: Optional[str] = Field(default=None, max_length=255)
    TrangThai: Optional[str] = Field(default=None, pattern="^(san_sang|dang_chay|loi|tat)$")


class DeviceResponse(BaseModel):
    """Một thiết bị biên đã lưu."""

    PK_MaThietBi: int
    TenThietBi: str
    DuongDanRTSP: str
    MoTaViTri: Optional[str] = None
    TrangThai: str
    ThoiGianTao: datetime

    model_config = {"from_attributes": True}
