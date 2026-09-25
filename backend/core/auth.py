"""Tạo và kiểm tra token JWT. Logic: gắn hạn dùng/loại token rồi mã hóa HS256, giải mã kiểm tra đúng loại."""

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from core.config import settings


def create_access_token(
    data: dict,
    expires_delta: timedelta | None = None,
) -> tuple[str, datetime]:
    """
    Tạo access token JWT.

    Logic: hạn dùng mặc định theo cấu hình, gắn loại "access".
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta
        or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    token = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return token, expire


def create_refresh_token(
    data: dict,
    expires_delta: timedelta | None = None,
) -> tuple[str, datetime]:
    """
    Tạo refresh token JWT hạn dài.

    Logic: hạn dùng mặc định theo ngày trong cấu hình, gắn loại "refresh".
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta
        or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    to_encode.update({"exp": expire, "type": "refresh"})
    token = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return token, expire


def verify_token(token: str, token_type: str = "access") -> dict | None:
    """
    Giải mã và kiểm tra token.

    Logic: sai chữ ký hoặc khác loại token thì trả None.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        if payload.get("type") != token_type:
            return None
        return payload
    except JWTError:
        return None
