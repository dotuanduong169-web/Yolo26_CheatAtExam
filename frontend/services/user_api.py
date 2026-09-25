"""Lớp gọi API hồ sơ người dùng: xem, cập nhật, đổi mật khẩu.
Luồng chính: trang cài đặt gọi hàm này kèm token xác thực."""

import logging

import requests

from config import API_BASE_URL
from utils.http import get_auth_headers

logger = logging.getLogger(__name__)


def get_user(session: requests.Session) -> dict | None:
    """Lấy hồ sơ người dùng hiện tại. Lỗi thì trả None."""
    try:
        res = session.get(
            f"{API_BASE_URL}/users/profile",
            headers=get_auth_headers(),
        )
        if res.status_code == 200:
            return res.json()

        logger.warning(f"get_user failed: {res.status_code}")
        return None

    except requests.RequestException as exc:
        logger.warning(f"get_user error: {exc}")
        return None


def update_user(
    session: requests.Session,
    full_name: str,
    email: str,
) -> tuple[bool, str | dict]:
    """Cập nhật hồ sơ. Trả về (thành công, dữ liệu hoặc thông báo lỗi)."""
    try:
        res = session.put(
            f"{API_BASE_URL}/users/update",
            json={"full_name": full_name, "email": email},
            headers=get_auth_headers(),
        )

        if res.status_code == 200:
            return True, res.json()
        if res.status_code == 401:
            return False, "Session expired. Please log in again"
        if res.status_code == 409:
            return False, "Email is already in use"

        detail = res.json().get("detail", "Server error") if res.text else "Server error"
        return False, detail

    except requests.RequestException as exc:
        return False, f"Connection error: {exc}"


def change_password(
    session: requests.Session,
    old_password: str,
    new_password: str,
) -> tuple[bool, str | dict]:
    """Đổi mật khẩu. Trả về (thành công, dữ liệu hoặc thông báo lỗi)."""
    try:
        res = session.put(
            f"{API_BASE_URL}/users/change-password",
            json={"old_password": old_password, "new_password": new_password},
            headers=get_auth_headers(),
        )

        if res.status_code == 200:
            return True, res.json()
        if res.status_code == 401:
            return False, "Session expired. Please log in again"
        if res.status_code == 422:
            detail = res.json().get("detail", "Old password is incorrect") if res.text else "Old password is incorrect"
            return False, detail

        detail = res.json().get("detail", "Server error") if res.text else "Server error"
        return False, detail

    except requests.RequestException as exc:
        return False, f"Connection error: {exc}"