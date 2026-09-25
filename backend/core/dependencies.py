"""Dependency xác thực và thông tin request. Logic: ưu tiên cookie trước header, chặn token đã đăng xuất."""

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from core.config import settings
from core.logger import get_logger
from core.token_blacklist import TokenBlacklist
from database.database import get_db
from models.user import User
from sqlalchemy.orm import Session

logger = get_logger(__name__)
security = HTTPBearer(auto_error=False)


def get_client_ip(request: Request) -> str:
    """
    Lấy IP client từ request.

    Logic: ưu tiên X-Forwarded-For trước X-Real-IP rồi mới tới kết nối trực tiếp.
    """
    if forwarded := request.headers.get("x-forwarded-for"):
        return forwarded.split(",")[0].strip()

    if real_ip := request.headers.get("x-real-ip"):
        return real_ip

    return request.client.host if request.client else "unknown"


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """
    Xác thực user hiện tại bằng JWT.

    Logic: ưu tiên cookie trước header, chặn blacklist khi logout, thiếu user_id thì từ chối.
    """
    # Ưu tiên cookie trước header
    token = request.cookies.get("access_token")
    if not token and credentials:
        token = credentials.credentials

    if not token:
        logger.warning("Unauthorized: no token provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    # Chặn token đã đăng xuất
    if TokenBlacklist.is_blacklisted(token):
        logger.warning("Unauthorized: token is blacklisted")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
        )

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        user_id: int | None = payload.get("user_id")

        if user_id is None:
            logger.warning("Unauthorized: token missing user_id")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )

        logger.debug(f"User authenticated: {user_id}")
        
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
             logger.warning(f"Unauthorized: user {user_id} not found in DB")
             raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )
        return user

    except JWTError as exc:
        logger.warning(f"Unauthorized: JWT validation failed — {exc}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalid",
        )
