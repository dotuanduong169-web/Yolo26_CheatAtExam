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
    """Thí sinh vào thi chỉ cần SBD (+ mã ca thi để phân biệt khi trùng SBD khác ca).

    VaiTro: front = webcam máy tính, side = điện thoại đặt sau/bên.
    Lượt join mang role=side sẽ dùng đúng phiên con đang mở của thí sinh.
    """

    SBD: str = Field(..., min_length=1, max_length=50)
    FK_MaPhienGiamSat: Optional[int] = None
    VaiTro: str = Field(default="front", pattern="^(front|side)$")


class CameraStreamResponse(BaseModel):
    """Một luồng camera của phiên con (dùng cho dashboard và link camera phụ)."""

    PK_MaStream: int
    VaiTro: str
    Token: Optional[str] = None
    TrangThai: str = "dang_hoat_dong"
    LanCuoiNhan: Optional[datetime] = None
    ThoiGianTao: datetime

    model_config = {"from_attributes": True}


class StreamTokenResponse(BaseModel):
    """Token + đường dẫn mở luồng camera (front/side) cho giám thị gửi thí sinh."""

    PK_MaPhienGiamSat: int
    VaiTro: str
    token: str
    exam_url: str


class CandidateJoinResponse(BaseModel):
    """Kết quả vào thi: phiên con + token nộp frame theo vai trò camera."""

    PK_MaPhienGiamSat: int
    VaiTro: str = "front"
    token: str
    candidate: CandidateResponse
