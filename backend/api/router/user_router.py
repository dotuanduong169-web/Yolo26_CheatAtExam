"""Endpoint người dùng cho đăng ký, đăng nhập, hồ sơ và phiên token.
Logic chính: access_token lưu cookie kèm body, đăng xuất thu hồi token rồi xóa cookie.
"""

from typing import Optional

from fastapi import APIRouter, Cookie, Depends, Request, Response
from sqlalchemy.orm import Session

from core.dependencies import get_client_ip, get_current_user
from core.security import get_cookie_settings
from database.database import get_db
from models.user import User
from schemas.common import MessageResponse, TokenResponse
from schemas.user import ChangePassword, UserCreate, UserLogin, UserResponse, UserUpdate
from service.user_service import (
    change_user_password,
    get_profile,
    login_user,
    logout_user,
    refresh_access_token,
    register_user,
    update_profile,
)

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/register", response_model=UserResponse)
def register(
    user: UserCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    """Đăng ký tài khoản mới. Ghi nhận IP client để theo dõi nguồn đăng ký."""
    return register_user(db, user, get_client_ip(request))


@router.post("/login", response_model=TokenResponse)
def login(
    user: UserLogin,
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
):
    """Đăng nhập và nhận token. Token vừa trả trong body vừa ghi vào cookie HttpOnly."""
    result = login_user(db, user.email, user.password, get_client_ip(request))
    cookie = get_cookie_settings()

    response.set_cookie(key="access_token", value=result["access_token"], **cookie)
    response.set_cookie(
        key="refresh_token",
        value=result["refresh_token"],
        max_age=7 * 24 * 60 * 60,
        httponly=True,
        secure=cookie.get("secure", False),
        samesite="lax",
    )

    return {
        "message": "Login successful",
        "user_id": result["user_id"],
        "role": result["role"],
        "access_token": result["access_token"],
        "refresh_token": result["refresh_token"],
    }


@router.get("/profile", response_model=UserResponse)
def get_user_profile(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lấy hồ sơ của người đang đăng nhập. Yêu cầu access_token hợp lệ."""
    return get_profile(db, user.user_id)


@router.put("/update", response_model=UserResponse)
def update_user(
    data: UserUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cập nhật hồ sơ người đang đăng nhập. Chỉ sửa tên hiển thị và email."""
    return update_profile(db, user.user_id, data)


@router.put("/change-password", response_model=MessageResponse)
def change_password(
    data: ChangePassword,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Đổi mật khẩu. Service đối chiếu mật khẩu cũ trước khi băm và lưu mật khẩu mới."""
    change_user_password(db, user.user_id, data.old_password, data.new_password)
    return {"message": "Password changed successfully"}


@router.post("/logout", response_model=MessageResponse)
def logout(
    response: Response,
    user: User = Depends(get_current_user),
    access_token: Optional[str] = Cookie(None),
    refresh_token: Optional[str] = Cookie(None),
):
    """Đăng xuất. Thu hồi token trên server rồi xóa cả hai cookie phiên."""
    logout_user(user.user_id, access_token, refresh_token)

    cookie = get_cookie_settings()
    for key in ("access_token", "refresh_token"):
        response.delete_cookie(
            key=key,
            path="/",
            httponly=True,
            secure=cookie.get("secure", False),
            samesite="lax",
        )

    return {"message": "Logout successful"}


@router.post("/refresh")
def refresh(
    response: Response,
    refresh_token: Optional[str] = Cookie(None),
):
    """Cấp access_token mới từ refresh_token trong cookie. Ghi token mới đè lên cookie cũ."""
    result = refresh_access_token(refresh_token)

    response.set_cookie(
        key="access_token",
        value=result["access_token"],
        **get_cookie_settings(),
    )

    return {
        "message": "Token refreshed successfully",
        "access_token": result["access_token"],
        "user_id": result["user_id"],
        "role": result["role"],
    }
