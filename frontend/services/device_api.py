"""Gọi API thiết bị biên: liệt kê, đăng ký, sửa, xóa."""

import logging

import requests

from config import API_BASE_URL
from utils.http import get_auth_headers

logger = logging.getLogger(__name__)


def list_devices(session: requests.Session) -> list:
    """Liệt kê thiết bị biên. Lỗi trả []."""
    try:
        res = session.get(
            f"{API_BASE_URL}/devices",
            headers=get_auth_headers(),
        )
        if res.status_code == 200:
            return res.json()
        logger.warning(f"list_devices failed: {res.status_code}")
        return []
    except requests.RequestException as exc:
        logger.warning(f"list_devices error: {exc}")
        return []


def create_device(session: requests.Session, name: str, rtsp: str, location: str = ""):
    """Đăng ký thiết bị mới. Trả response thô."""
    try:
        return session.post(
            f"{API_BASE_URL}/devices",
            json={"TenThietBi": name, "DuongDanRTSP": rtsp, "MoTaViTri": location or None},
            headers=get_auth_headers(),
        )
    except requests.RequestException as exc:
        logger.warning(f"create_device error: {exc}")
        return None


def update_device(session: requests.Session, device_id: int, data: dict):
    """Sửa thiết bị. Trả response thô."""
    try:
        return session.put(
            f"{API_BASE_URL}/devices/{device_id}",
            json=data,
            headers=get_auth_headers(),
        )
    except requests.RequestException as exc:
        logger.warning(f"update_device error: {exc}")
        return None


def delete_device(session: requests.Session, device_id: int):
    """Xóa thiết bị. Trả response thô."""
    try:
        return session.delete(
            f"{API_BASE_URL}/devices/{device_id}",
            headers=get_auth_headers(),
        )
    except requests.RequestException as exc:
        logger.warning(f"delete_device error: {exc}")
        return None
