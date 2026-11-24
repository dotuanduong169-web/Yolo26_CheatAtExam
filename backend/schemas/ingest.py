"""Schema ingest frame thi online.
Logic chính: frame JPEG + timestamp client để chống replay và đo trễ mạng.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class IngestAccepted(BaseModel):
    """Xác nhận đã nhận frame vào hàng đợi (202, không chờ infer)."""

    PK_MaPhienGiamSat: int
    queued: bool = True


class CandidateBehaviorStat(BaseModel):
    """Tổng hợp một loại hành vi của thí sinh (để lưới giám thị hiện đa hành vi)."""

    label: str
    total: int = 0
    pending: int = 0
    last_at: Optional[datetime] = None


class CandidateStatusItem(BaseModel):
    """Trạng thái 1 thí sinh cho lưới giám thị."""

    PK_MaThiSinh: int
    SBD: str
    HoTen: str
    Lop: Optional[str] = None
    PK_MaPhienGiamSat: Optional[int] = None
    dang_giam_sat: bool = False
    camera_front_active: bool = False
    camera_side_active: bool = False
    camera_side_joined: bool = False
    cho_kiem_tra: int = 0
    tong_su_kien: int = 0
    anh_moi_nhat: Optional[datetime] = None
    hanh_vi_moi_nhat: Optional[str] = None
    thoi_gian_vi_pham: Optional[datetime] = None
    # Danh sách hành vi đã ghi nhận (mỗi nhãn 1 dòng, mới nhất trước).
    behaviors: list[CandidateBehaviorStat] = Field(default_factory=list)
