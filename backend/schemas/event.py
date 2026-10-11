"""Schema sự kiện phát hiện cho liệt kê, xác minh và chi tiết.
Logic chính: chỉ lưu hành vi gian lận; người dùng xác minh đúng/sai kèm nhãn sửa.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, model_validator


class EventVerify(BaseModel):
    """Dữ liệu xác minh một sự kiện."""

    TrangThaiKiemTra: str = Field(..., pattern="^(dung|sai)$")
    LoaiHanhVi: Optional[str] = Field(default=None, max_length=100)
    NhanNguoiDung: Optional[str] = Field(default=None, max_length=100)


class EvidenceResponse(BaseModel):
    """Một bằng chứng ảnh/video của sự kiện."""

    PK_MaBangChung: int
    LoaiTep: str
    DuongDanTep: str
    ThoiGianTao: datetime

    model_config = {"from_attributes": True}


class EventResponse(BaseModel):
    """Một sự kiện gian lận kèm bằng chứng và tọa độ để vẽ lại."""

    PK_MaSuKien: int
    LoaiHanhVi: str
    NhanAI: Optional[str] = None
    NhanNguoiDung: Optional[str] = None
    ToaDo: Any
    DoTinCay: float
    ThoiGianPhatHien: datetime
    TrangThaiKiemTra: Optional[str] = None
    FK_MaPhienGiamSat: int
    evidences: list[EvidenceResponse] = []

    model_config = {"from_attributes": True}

    @model_validator(mode="after")
    def populate_legacy_labels(self):
        """Gán nhãn tương thích ngược từ trường LoaiHanhVi duy nhất."""
        if self.NhanAI is None:
            self.NhanAI = self.LoaiHanhVi
        if self.NhanNguoiDung is None:
            self.NhanNguoiDung = self.LoaiHanhVi
        return self

