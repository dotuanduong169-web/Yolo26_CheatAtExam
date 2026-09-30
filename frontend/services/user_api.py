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


def list_all_users(session: requests.Session, skip: int = 0, limit: int = 50) -> list:
    """Liệt kê toàn bộ người dùng trong hệ thống (chỉ admin)."""
    try:
        res = session.get(
            f"{API_BASE_URL}/users/list",
            params={"skip": skip, "limit": limit},
            headers=get_auth_headers(),
        )
        if res.status_code == 200:
            return res.json()
        logger.warning(f"list_all_users failed: {res.status_code}")
        return []
    except requests.RequestException as exc:
        logger.warning(f"list_all_users error: {exc}")
        return []


def admin_update_user(
    session: requests.Session,
    user_id: int,
    role: str | None = None,
    status: str | None = None,
    ho_va_ten: str | None = None,
) -> tuple[bool, str | dict]:
    """Admin cập nhật vai trò, trạng thái hoặc họ tên tài khoản người dùng."""
    try:
        payload = {}
        if role is not None:
            payload["VaiTro"] = role
        if status is not None:
            payload["TrangThai"] = status
        if ho_va_ten is not None:
            payload["HoVaTen"] = ho_va_ten

        res = session.put(
            f"{API_BASE_URL}/users/{user_id}",
            json=payload,
            headers=get_auth_headers(),
        )
        if res.status_code == 200:
            return True, res.json()
        detail = res.json().get("detail", "Lỗi server") if res.text else "Lỗi server"
        return False, detail
    except requests.RequestException as exc:
        return False, f"Lỗi kết nối: {exc}"


def admin_create_user(
    session: requests.Session,
    username: str,
    full_name: str,
    password: str,
    role: str = "teacher",
) -> tuple[bool, str | dict]:
    """Admin tạo tài khoản người dùng mới."""
    try:
        res = session.post(
            f"{API_BASE_URL}/users/create",
            json={
                "TenDangNhap": username,
                "HoVaTen": full_name,
                "MatKhau": password,
                "VaiTro": role,
            },
            headers=get_auth_headers(),
        )
        if res.status_code in (200, 201):
            return True, res.json()
        detail = res.json().get("detail", "Lỗi server") if res.text else "Lỗi server"
        return False, detail
    except requests.RequestException as exc:
        return False, f"Lỗi kết nối: {exc}"


