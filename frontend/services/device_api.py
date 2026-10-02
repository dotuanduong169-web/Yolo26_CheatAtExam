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


def test_device(session: requests.Session, device_id: int) -> dict:
    """Gọi API kiểm tra kết nối thực tế tới thiết bị camera/RTSP."""
    try:
        res = session.post(
            f"{API_BASE_URL}/devices/{device_id}/test",
            headers=get_auth_headers(),
            timeout=5,
        )
        if res.status_code == 200:
            return res.json()
        return {"online": False, "latency_ms": 0, "message": f"Lỗi kiểm tra ({res.status_code})"}
    except requests.RequestException as exc:
        logger.warning(f"test_device error: {exc}")
        return {"online": False, "latency_ms": 0, "message": "Không thể kết nối đến máy chủ"}


def get_ai_config(session: requests.Session) -> dict:
    """Lấy tham số cấu hình AI nhận diện đã lưu."""
    try:
        res = session.get(
            f"{API_BASE_URL}/devices/ai-config/get",
            headers=get_auth_headers(),
            timeout=5,
        )
        if res.status_code == 200:
            return res.json()
    except requests.RequestException:
        pass
    return {"conf_thresh": 0.75, "time_thresh": 2.5}


def save_ai_config(session: requests.Session, conf_thresh: float, time_thresh: float) -> bool:
    """Lưu tham số cấu hình AI nhận diện vào hệ thống."""
    try:
        res = session.post(
            f"{API_BASE_URL}/devices/ai-config/save",
            json={"conf_thresh": conf_thresh, "time_thresh": time_thresh},
            headers=get_auth_headers(),
            timeout=5,
        )
        return res.status_code == 200
    except requests.RequestException:
        return False


def ensure_machine_camera(session: requests.Session) -> dict | None:
    """Tìm thiết bị webcam của máy (RTSP '0'), chưa có thì tự đăng ký. Lỗi trả None."""
    for dev in list_devices(session):
        if dev.get("DuongDanRTSP") == "0":
            return dev
    res = create_device(session, "Camera may", "0", "webcam cua may chu")
    if res is not None and res.status_code == 200:
        return res.json()
    logger.warning("ensure_machine_camera failed")
    return None

