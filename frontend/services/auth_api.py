"""Lớp gọi API xác thực: đăng nhập, đăng ký, đăng xuất, làm mới token.
Luồng chính: trang Streamlit gọi hàm này -> chuyển tiếp tới FastAPI /users/*."""

import logging

import requests

from config import API_BASE_URL
from utils.http import get_auth_headers

logger = logging.getLogger(__name__)


def login(session: requests.Session, email: str, password: str):
    """Đăng nhập và trả về response (token nằm trong JSON)."""
    return session.post(
        f"{API_BASE_URL}/users/login",
        json={"email": email, "password": password},
    )


def register(session: requests.Session, full_name: str, email: str, password: str):
    """Đăng ký tài khoản người dùng mới."""
    return session.post(
        f"{API_BASE_URL}/users/register",
        json={"email": email, "password": password, "full_name": full_name},
    )


def logout(session: requests.Session):
    """Đăng xuất — vô hiệu hóa token đang dùng."""
    try:
        return session.post(
            f"{API_BASE_URL}/users/logout",
            headers=get_auth_headers(),
        )
    except requests.RequestException as exc:
        logger.warning(f"Logout API error: {exc}")
        return None


def refresh_token(session: requests.Session):
    """Làm mới access token bằng refresh token trong cookie."""
    try:
        return session.post(
            f"{API_BASE_URL}/users/refresh",
            headers=get_auth_headers(),
        )
    except requests.RequestException as exc:
        logger.warning(f"Refresh token error: {exc}")
        return None
