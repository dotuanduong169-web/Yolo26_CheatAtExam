"""Endpoint người dùng cho đăng ký, đăng nhập, hồ sơ và phiên token.
Logic chính: đăng nhập bằng TenDangNhap; access_token lưu cookie kèm body, đăng xuất thu hồi token rồi xóa cookie.
"""

from typing import Optional

from fastapi import APIRouter, Cookie, Depends, Request, Response
from sqlalchemy.orm import Session

from core.dependencies import get_client_ip, get_current_user
from core.exceptions import AuthorizationError
from core.security import get_cookie_settings
from crud.user_crud import admin_update_user, list_users
from database.database import get_db
from models.user import User
from schemas.common import MessageResponse, TokenResponse
from schemas.user import (
    ChangePassword,
    UserAdminUpdate,
    UserCreate,
    UserLogin,
    UserResponse,
    UserUpdate,
)
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


def _require_admin(user: User) -> None:
    """Chặn user thường khỏi endpoint quản trị."""
    if user.VaiTro != "admin":
        raise AuthorizationError(detail="Admin only")


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
    result = login_user(db, user.TenDangNhap, user.MatKhau, get_client_ip(request))
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
        "role": result["vai_tro"],
        "access_token": result["access_token"],
        "refresh_token": result["refresh_token"],
    }


@router.get("/profile", response_model=UserResponse)
def get_user_profile(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lấy hồ sơ của người đang đăng nhập. Yêu cầu access_token hợp lệ."""
    return get_profile(db, user.PK_MaNguoiDung)


@router.put("/update", response_model=UserResponse)
def update_user(
    data: UserUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cập nhật hồ sơ người đang đăng nhập. Chỉ sửa họ tên."""
    return update_profile(db, user.PK_MaNguoiDung, data)


@router.put("/change-password", response_model=MessageResponse)
def change_password(
    data: ChangePassword,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Đổi mật khẩu. Service đối chiếu mật khẩu cũ trước khi băm và lưu mật khẩu mới."""
    change_user_password(db, user.PK_MaNguoiDung, data.MatKhauCu, data.MatKhauMoi)
    return {"message": "Password changed successfully"}


@router.post("/logout", response_model=MessageResponse)
def logout(
    response: Response,
    user: User = Depends(get_current_user),
    access_token: Optional[str] = Cookie(None),
    refresh_token: Optional[str] = Cookie(None),
):
    """Đăng xuất. Thu hồi token trên server rồi xóa cả hai cookie phiên."""
    logout_user(user.PK_MaNguoiDung, access_token, refresh_token)

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
        "role": result["vai_tro"],
    }


@router.get("/list", response_model=list[UserResponse])
def get_users(
    skip: int = 0,
    limit: int = 50,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Liệt kê người dùng. Chỉ admin."""
    _require_admin(user)
    return list_users(db, skip, limit)


@router.put("/{user_id}", response_model=UserResponse)
def admin_update(
    user_id: int,
    data: UserAdminUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Admin đổi vai trò/trạng thái tài khoản. Chỉ admin."""
    from fastapi import HTTPException

    from core.exceptions import NotFoundError

    _require_admin(user)
    updated = admin_update_user(db, user_id, data.VaiTro, data.TrangThai)
    if not updated:
        raise NotFoundError(detail="User not found")
    return updated
