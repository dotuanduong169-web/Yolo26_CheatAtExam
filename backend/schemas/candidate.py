"""Schema thí sinh cho nhập danh sách, liệt kê và vào thi.
Logic chính: SBD duy nhất trong một ca thi; vào thi chỉ cần SBD.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CandidateItem(BaseModel):
    """Một thí sinh trong danh sách nhập."""

    SBD: str = Field(..., min_length=1, max_length=50)
    HoTen: str = Field(..., min_length=1, max_length=255)
    Lop: Optional[str] = Field(default=None, max_length=100)


class CandidateImport(BaseModel):
    """Danh sách thí sinh của một ca thi do giám thị nhập."""

    FK_MaPhienGiamSat: int
    candidates: list[CandidateItem] = Field(..., min_length=1)


class CandidateResponse(BaseModel):
    """Một thí sinh đã lưu."""

    PK_MaThiSinh: int
    SBD: str
    HoTen: str
    Lop: Optional[str] = None
    FK_MaPhienGiamSat: int
    ThoiGianTao: datetime

    model_config = {"from_attributes": True}


class CandidateJoin(BaseModel):
    """Thí sinh vào thi chỉ cần SBD (+ mã ca thi để phân biệt khi trùng SBD khác ca)."""

    SBD: str = Field(..., min_length=1, max_length=50)
    FK_MaPhienGiamSat: Optional[int] = None


class CandidateJoinResponse(BaseModel):
    """Kết quả vào thi: phiên con + token nộp frame."""

    PK_MaPhienGiamSat: int
    token: str
    candidate: CandidateResponse
