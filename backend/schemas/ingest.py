"""Schema ingest frame thi online.
Logic chính: frame JPEG + timestamp client để chống replay và đo trễ mạng.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class IngestAccepted(BaseModel):
    """Xác nhận đã nhận frame vào hàng đợi (202, không chờ infer)."""

    PK_MaPhienGiamSat: int
    queued: bool = True


class CandidateStatusItem(BaseModel):
    """Trạng thái 1 thí sinh cho lưới giám thị."""

    PK_MaThiSinh: int
    SBD: str
    HoTen: str
    Lop: Optional[str] = None
    PK_MaPhienGiamSat: Optional[int] = None
    dang_giam_sat: bool = False
    cho_kiem_tra: int = 0
    tong_su_kien: int = 0
    anh_moi_nhat: Optional[datetime] = None
