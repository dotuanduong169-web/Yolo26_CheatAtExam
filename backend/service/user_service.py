"""Quản lý người dùng: đăng ký, đăng nhập, hồ sơ, token.
Luồng chính: kiểm tra rate-limit theo IP → xác thực trong DB → cấp hoặc thu hồi JWT."""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DBSession

from core.auth import create_access_token, create_refresh_token, verify_token
from core.exceptions import (
    AuthenticationError,
    ConflictError,
    NotFoundError,
    RateLimitError,
    ValidationError,
)
from database.database import SessionLocal
from core.logger import get_logger
from core.rate_limiter import RateLimiter
from core.security import get_cookie_settings, hash_password, verify_password
from core.token_blacklist import TokenBlacklist
from crud.user_crud import (
    create_user,
    get_user_by_id,
    get_user_by_username,
    update_user_password,
    update_user_profile,
)
from models.user import User
from schemas.user import UserCreate, UserUpdate

logger = get_logger(__name__)


# ── Registration ────────────────────────────────────────────


def register_user(db: DBSession, user_data: UserCreate, client_ip: str) -> User:
    """Đăng ký người dùng mới, chặn spam theo IP.
    Điểm logic: vượt ngưỡng thử thì chặn; tên đăng nhập trùng thì ghi nhận 1 lượt;
    thành công thì xóa đếm rate-limit.

    Raises:
        RateLimitError: Quá nhiều lượt đăng ký từ IP này.
        ConflictError: Tên đăng nhập đã được đăng ký.
    """
    rate_limiter = RateLimiter()
    reg_key = f"reg:{client_ip}"

    if rate_limiter.is_rate_limited(reg_key):
        minutes = _minutes_until_reset(rate_limiter, reg_key)
        logger.warning(f"Registration rate-limited for IP: {client_ip}")
        raise RateLimitError(
            detail=f"Too many registration attempts. Try again in {minutes} minutes."
        )

    if get_user_by_username(db, user_data.TenDangNhap):
        rate_limiter.record_attempt(reg_key)
        logger.warning(f"Registration with existing username: {user_data.TenDangNhap}")
        raise ConflictError(detail="TenDangNhap already exists")

    logger.info(f"Registering user: {user_data.TenDangNhap} from {client_ip}")

    try:
        created_user = create_user(db, user_data)
    except IntegrityError:
        db.rollback()
        logger.error("Database integrity error during registration", exc_info=True)
        raise ConflictError(detail="Failed to create user — duplicate username")

    rate_limiter.reset_for_ip(reg_key)
    logger.info(f"User registered: {user_data.TenDangNhap}")
    return created_user


# ── Authentication ──────────────────────────────────────────


def login_user(
    db: DBSession,
    username: str,
    password: str,
    client_ip: str,
) -> dict:
    """
    Xác thực đăng nhập và cấp cặp JWT access/refresh.
    Điểm logic: sai quá ngưỡng theo IP thì chặn; tài khoản khóa thì từ chối;
    đúng thì xóa đếm và cấp token mới.

    Returns:
        Dict gồm ``user_id``, ``vai_tro``, ``access_token``, ``refresh_token``.

    Raises:
        RateLimitError: Quá nhiều lượt đăng nhập từ IP này.
        AuthenticationError: Tên đăng nhập hoặc mật khẩu sai, hoặc tài khoản khóa.
    """
    rate_limiter = RateLimiter()

    if rate_limiter.is_rate_limited(client_ip):
        minutes = _minutes_until_reset(rate_limiter, client_ip)
        logger.warning(f"Login rate-limited for IP: {client_ip}")
        raise RateLimitError(
            detail=f"Too many login attempts. Try again in {minutes} minutes."
        )

    logger.info(f"Login attempt: {username} from {client_ip}")

    db_user = get_user_by_username(db, username)
    if not db_user or not verify_password(password, db_user.MatKhau):
        rate_limiter.record_attempt(client_ip)
        logger.warning(f"Login failed for: {username} from {client_ip}")
        raise AuthenticationError(detail="Invalid username or password")

    if db_user.TrangThai != "hoat_dong":
        logger.warning(f"Login blocked for locked account: {username}")
        raise AuthenticationError(detail="Account is locked")

    # Thành công — xóa đếm rate-limit của IP
    rate_limiter.reset_for_ip(client_ip)

    access_token, _ = create_access_token(data={"user_id": db_user.PK_MaNguoiDung})
    refresh_token, _ = create_refresh_token(data={"user_id": db_user.PK_MaNguoiDung})

    logger.info(f"Login successful: {username}")

    return {
        "user_id": db_user.PK_MaNguoiDung,
        "vai_tro": db_user.VaiTro,
        "access_token": access_token,
        "refresh_token": refresh_token,
    }


# ── Profile ─────────────────────────────────────────────────


def get_profile(db: DBSession, user_id: int) -> User:
    """Lấy hồ sơ người dùng theo ID.
    Điểm logic: không tồn tại thì báo lỗi thay vì trả rỗng.

    Raises:
        NotFoundError: Người dùng không tồn tại.
    """
    user = get_user_by_id(db, user_id)
    if not user:
        raise NotFoundError(detail="User not found")
    return user


def update_profile(db: DBSession, user_id: int, data: UserUpdate) -> User:
    """
    Cập nhật họ tên người dùng.

    Raises:
        NotFoundError: Người dùng không tồn tại.
    """
    user = update_user_profile(db, user_id, data.HoVaTen)
    if not user:
        raise NotFoundError(detail="User not found")
    logger.info(f"Profile updated for user: {user_id}")
    return user


def change_user_password(
    db: DBSession,
    user_id: int,
    old_password: str,
    new_password: str,
) -> None:
    """
    Đổi mật khẩu sau khi đối chiếu mật khẩu cũ.
    Điểm logic: phải khớp mật khẩu cũ đã băm thì mới cho băm và lưu mật khẩu mới.

    Raises:
        NotFoundError: Người dùng không tồn tại.
        ValidationError: Mật khẩu cũ không đúng.
    """
    user = get_user_by_id(db, user_id)
    if not user:
        raise NotFoundError(detail="User not found")

    if not verify_password(old_password, user.MatKhau):
        raise ValidationError(detail="Old password is incorrect")

    update_user_password(db, user_id, hash_password(new_password))
    logger.info(f"Password changed for user: {user_id}")


# ── Token Management ────────────────────────────────────────


def logout_user(
    user_id: int,
    access_token: Optional[str],
    refresh_token: Optional[str],
) -> None:
    """Đăng xuất: đưa access và refresh token vào danh sách cấm."""
    logger.info(f"Logout for user: {user_id}")

    if access_token:
        _blacklist_token(access_token, "access", user_id)
    if refresh_token:
        _blacklist_token(refresh_token, "refresh", user_id)


def refresh_access_token(refresh_token: Optional[str]) -> dict:
    """
    Cấp access token mới từ refresh token còn hiệu lực.
    Điểm logic: thiếu token, bị thu hồi, sai loại hoặc mất user_id đều từ chối.

    Returns:
        Dict gồm ``access_token``, ``user_id`` và ``vai_tro``.

    Raises:
        AuthenticationError: Refresh token thiếu, bị thu hồi hoặc không hợp lệ.
    """
    if not refresh_token:
        raise AuthenticationError(detail="Refresh token not provided")

    if TokenBlacklist.is_blacklisted(refresh_token):
        raise AuthenticationError(detail="Refresh token has been revoked")

    payload = verify_token(refresh_token, token_type="refresh")
    if not payload:
        raise AuthenticationError(detail="Invalid refresh token")

    user_id = payload.get("user_id")
    if not user_id:
        raise AuthenticationError(detail="Invalid refresh token")

    with SessionLocal() as db:
        db_user = get_user_by_id(db, user_id)
        if not db_user:
            raise AuthenticationError(detail="User not found")
        role = db_user.VaiTro

    access_token, _ = create_access_token(data={"user_id": user_id})
    logger.info(f"Access token refreshed for user: {user_id}")

    return {"access_token": access_token, "user_id": user_id, "vai_tro": role}


# ── Helpers (private) ───────────────────────────────────────


def _blacklist_token(token: str, token_type: str, user_id: int) -> None:
    """Đưa token vào danh sách cấm theo mốc hết hạn trong payload."""
    try:
        payload = verify_token(token, token_type=token_type)
        if payload and (exp := payload.get("exp")):
            TokenBlacklist.add(token, datetime.fromtimestamp(exp, tz=timezone.utc))
            logger.debug(f"{token_type.title()} token blacklisted for user: {user_id}")
    except Exception as exc:
        logger.debug(f"Could not blacklist {token_type} token: {exc}")


def _minutes_until_reset(rate_limiter: RateLimiter, key: str) -> int:
    """Tính số phút còn lại tới khi cửa sổ rate-limit được reset."""
    reset_time = rate_limiter.get_reset_time(key)
    delta = (reset_time - datetime.now(timezone.utc)).total_seconds()
    return max(1, int(delta / 60))
