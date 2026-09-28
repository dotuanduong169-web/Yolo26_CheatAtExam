"""Gọi API sự kiện: liệt kê theo phiên, chi tiết, xác minh, tải ảnh bằng chứng."""

import logging

import requests

from config import API_BASE_URL
from utils.http import get_auth_headers

logger = logging.getLogger(__name__)


def list_session_events(
    session: requests.Session,
    session_id: int,
    trang_thai: str = "",
    skip: int = 0,
    limit: int = 50,
) -> list:
    """Liệt kê sự kiện của phiên. Lỗi trả []."""
    try:
        params = {"skip": skip, "limit": limit}
        if trang_thai:
            params["trang_thai"] = trang_thai
        res = session.get(
            f"{API_BASE_URL}/events/session/{session_id}",
            params=params,
            headers=get_auth_headers(),
        )
        if res.status_code == 200:
            return res.json()
        logger.warning(f"list_session_events failed: {res.status_code}")
        return []
    except requests.RequestException as exc:
        logger.warning(f"list_session_events error: {exc}")
        return []


def get_event_detail(session: requests.Session, event_id: int) -> dict | None:
    """Chi tiết một sự kiện kèm bằng chứng và tọa độ. Lỗi trả None."""
    try:
        res = session.get(
            f"{API_BASE_URL}/events/{event_id}",
            headers=get_auth_headers(),
        )
        if res.status_code == 200:
            return res.json()
        logger.warning(f"get_event_detail failed: {res.status_code}")
        return None
    except requests.RequestException as exc:
        logger.warning(f"get_event_detail error: {exc}")
        return None


def verify_event(
    session: requests.Session,
    event_id: int,
    trang_thai: str,
    nhan_nguoi_dung: str = "",
):
    """Xác minh đúng/sai kèm nhãn sửa. Trả response thô."""
    try:
        return session.patch(
            f"{API_BASE_URL}/events/{event_id}",
            json={"TrangThaiKiemTra": trang_thai, "NhanNguoiDung": nhan_nguoi_dung or None},
            headers=get_auth_headers(),
        )
    except requests.RequestException as exc:
        logger.warning(f"verify_event error: {exc}")
        return None


def get_evidence_bytes(session: requests.Session, evidence_id: int) -> bytes | None:
    """Tải ảnh bằng chứng. Lỗi trả None."""
    try:
        res = session.get(
            f"{API_BASE_URL}/events/evidences/{evidence_id}/file",
            headers=get_auth_headers(),
        )
        if res.status_code == 200:
            return res.content
        return None
    except requests.RequestException as exc:
        logger.warning(f"get_evidence_bytes error: {exc}")
        return None
