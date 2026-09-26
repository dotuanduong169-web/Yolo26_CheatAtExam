"""Schema phiên giám sát cho tạo ca, liệt kê và chi tiết.
Logic chính: phiên gắn một thiết bị biên và một người tạo; kết thúc khi có ThoiGianKetThuc.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SessionCreate(BaseModel):
    """Dữ liệu mở phiên giám sát mới."""

    PhongThi: Optional[str] = Field(default=None, max_length=50)
    MonThi: Optional[str] = Field(default=None, max_length=255)
    FK_MaThietBi: int


class SessionResponse(BaseModel):
    """Một phiên giám sát."""

    PK_MaPhienGiamSat: int
    ThoiGianBatDau: datetime
    ThoiGianKetThuc: Optional[datetime] = None
    TrangThai: str
    PhongThi: Optional[str] = None
    MonThi: Optional[str] = None
    FK_MaNguoiDung: int
    FK_MaThietBi: int
    ThoiGianTao: datetime

    model_config = {"from_attributes": True}


class SessionListItem(BaseModel):
    """Một dòng trong danh sách phiên, kèm số sự kiện gian lận."""

    PK_MaPhienGiamSat: int
    PhongThi: Optional[str] = None
    MonThi: Optional[str] = None
    ThoiGianBatDau: datetime
    ThoiGianKetThuc: Optional[datetime] = None
    TrangThai: str
    so_su_kien: int = 0

    model_config = {"from_attributes": True}


class SessionSummaryResponse(BaseModel):
    """Tóm tắt toàn hệ thống cho dashboard."""

    tong_phien: int
    dang_giam_sat: int
    tong_su_kien: int
    cho_kiem_tra: int


class SessionDetailResponse(BaseModel):
    """Chi tiết phiên gồm danh sách sự kiện gian lận."""

    session: SessionResponse
    events: list = []
