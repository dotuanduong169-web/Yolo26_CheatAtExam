"""Schema người dùng cho đăng ký, đăng nhập và hồ sơ.
Logic chính: đăng nhập bằng TenDangNhap (duy nhất), mật khẩu có chữ hoa và chữ số.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# ── Yêu cầu ────────────────────────────────────────────────


class UserCreate(BaseModel):
    """Dữ liệu đăng ký tài khoản mới."""

    TenDangNhap: str = Field(..., min_length=3, max_length=255)
    MatKhau: str = Field(..., min_length=6, max_length=100)
    HoVaTen: str = Field(..., min_length=3, max_length=255)
    VaiTro: str = Field(default="teacher", pattern="^(admin|teacher)$")

    @field_validator("MatKhau")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Kiểm tra mật khẩu có ít nhất một chữ hoa và một chữ số."""
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserLogin(BaseModel):
    """Dữ liệu đăng nhập bằng tên đăng nhập và mật khẩu."""

    TenDangNhap: str
    MatKhau: str


class UserUpdate(BaseModel):
    """Dữ liệu cập nhật họ tên (tên đăng nhập không đổi)."""

    HoVaTen: str = Field(..., min_length=3, max_length=255)


class ChangePassword(BaseModel):
    """Dữ liệu đổi mật khẩu, mật khẩu mới phải có chữ hoa và chữ số."""

    MatKhauCu: str
    MatKhauMoi: str = Field(..., min_length=6, max_length=100)

    @field_validator("MatKhauMoi")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        """Kiểm tra mật khẩu mới có ít nhất một chữ hoa và một chữ số."""
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


# ── Phản hồi ───────────────────────────────────────────────


class UserResponse(BaseModel):
    """Hồ sơ người dùng công khai, không chứa mật khẩu."""

    PK_MaNguoiDung: int
    TenDangNhap: str
    HoVaTen: str
    VaiTro: str
    TrangThai: str
    ThoiGianTao: datetime

    model_config = {"from_attributes": True}


class UserAdminUpdate(BaseModel):
    """Admin đổi vai trò/trạng thái tài khoản."""

    VaiTro: Optional[str] = Field(default=None, pattern="^(admin|teacher)$")
    TrangThai: Optional[str] = Field(default=None, pattern="^(hoat_dong|khoa)$")
