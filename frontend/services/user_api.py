"""Gọi API hồ sơ: xem, cập nhật họ tên, đổi mật khẩu."""

import logging

import requests

from config import API_BASE_URL
from utils.http import get_auth_headers

logger = logging.getLogger(__name__)


def get_user(session: requests.Session) -> dict | None:
    """Lấy hồ sơ hiện tại. Lỗi trả None."""
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


def update_user(session: requests.Session, full_name: str) -> tuple[bool, str | dict]:
    """Cập nhật họ tên. Trả (thành công, dữ liệu hoặc lỗi)."""
    try:
        res = session.put(
            f"{API_BASE_URL}/users/update",
            json={"HoVaTen": full_name},
            headers=get_auth_headers(),
        )

        if res.status_code == 200:
            return True, res.json()
        if res.status_code == 401:
            return False, "Phiên hết hạn. Vui lòng đăng nhập lại"

        detail = res.json().get("detail", "Lỗi server") if res.text else "Lỗi server"
        return False, detail

    except requests.RequestException as exc:
        return False, f"Lỗi kết nối: {exc}"


def change_password(
    session: requests.Session,
    old_password: str,
    new_password: str,
) -> tuple[bool, str | dict]:
    """Đổi mật khẩu. Trả (thành công, dữ liệu hoặc lỗi)."""
    try:
        res = session.put(
            f"{API_BASE_URL}/users/change-password",
            json={"MatKhauCu": old_password, "MatKhauMoi": new_password},
            headers=get_auth_headers(),
        )

        if res.status_code == 200:
            return True, res.json()
        if res.status_code == 401:
            return False, "Phiên hết hạn. Vui lòng đăng nhập lại"
        if res.status_code == 422:
            detail = res.json().get("detail", "Mật khẩu cũ không đúng") if res.text else "Mật khẩu cũ không đúng"
            return False, detail

        detail = res.json().get("detail", "Lỗi server") if res.text else "Lỗi server"
        return False, detail

    except requests.RequestException as exc:
        return False, f"Lỗi kết nối: {exc}"
