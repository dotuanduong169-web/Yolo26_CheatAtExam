"""Gọi API xác thực: đăng nhập, đăng ký, đăng xuất, làm mới token."""

import logging

import requests

from config import API_BASE_URL
from utils.http import get_auth_headers

logger = logging.getLogger(__name__)


def login(session: requests.Session, username: str, password: str):
    """Đăng nhập bằng tên đăng nhập, token nằm trong body JSON."""
    return session.post(
        f"{API_BASE_URL}/users/login",
        json={"TenDangNhap": username, "MatKhau": password},
    )


def register(session: requests.Session, username: str, full_name: str, password: str):
    """Đăng ký tài khoản mới."""
    return session.post(
        f"{API_BASE_URL}/users/register",
        json={"TenDangNhap": username, "HoVaTen": full_name, "MatKhau": password},
    )


def logout(session: requests.Session):
    """Đăng xuất, thu hồi token."""
    try:
        return session.post(
            f"{API_BASE_URL}/users/logout",
            headers=get_auth_headers(),
        )
    except requests.RequestException as exc:
        logger.warning(f"Logout API error: {exc}")
        return None


def refresh_token(session: requests.Session):
    """Làm mới access token bằng refresh token cookie."""
    try:
        return session.post(
            f"{API_BASE_URL}/users/refresh",
            headers=get_auth_headers(),
        )
    except requests.RequestException as exc:
        logger.warning(f"Refresh token error: {exc}")
        return None
