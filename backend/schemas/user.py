"""Schema người dùng cho đăng ký, đăng nhập và hồ sơ.
Logic chính: mật khẩu bắt buộc có chữ hoa và chữ số, phản hồi công khai không lộ mật khẩu.
"""

from pydantic import BaseModel, EmailStr, Field, field_validator


# ── Yêu cầu ────────────────────────────────────────────────


class UserCreate(BaseModel):
    """Dữ liệu đăng ký tài khoản mới."""

    email: EmailStr
    password: str = Field(..., min_length=6, max_length=100)
    full_name: str = Field(..., min_length=3, max_length=100)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Kiểm tra mật khẩu có ít nhất một chữ hoa và một chữ số."""
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserLogin(BaseModel):
    """Dữ liệu đăng nhập bằng email và mật khẩu."""

    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    """Dữ liệu cập nhật tên hiển thị và email."""

    full_name: str = Field(..., min_length=3, max_length=100)
    email: EmailStr


class ChangePassword(BaseModel):
    """Dữ liệu đổi mật khẩu, mật khẩu mới phải có chữ hoa và chữ số."""

    old_password: str
    new_password: str = Field(..., min_length=6, max_length=100)

    @field_validator("new_password")
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
    """Hồ sơ người dùng công khai, không chứa trường nhạy cảm như mật khẩu."""

    user_id: int
    email: str
    full_name: str
    role: str

    model_config = {"from_attributes": True}
