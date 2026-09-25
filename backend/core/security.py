"""Băm mật khẩu và cấu hình cookie. Logic: bcrypt cho mật khẩu, cookie siết secure khi production."""

from passlib.context import CryptContext

from core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Băm mật khẩu gốc bằng bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """So khớp mật khẩu gốc với mã băm bcrypt."""
    return pwd_context.verify(plain_password, hashed_password)


def get_cookie_settings() -> dict:
    """
    Trả cấu hình cookie theo môi trường.

    Logic: development cho phép HTTP, production bắt buộc HTTPS.
    """
    return {
        "httponly": True,
        "secure": settings.is_production,
        "samesite": "lax",
        "max_age": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }