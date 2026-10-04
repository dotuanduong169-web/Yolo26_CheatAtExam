"""Gọi API lịch sử: danh sách phiên, tóm tắt, chi tiết, xóa phiên."""

import logging

import requests

from config import API_BASE_URL
from utils.http import get_auth_headers

logger = logging.getLogger(__name__)


def get_history(
    session: requests.Session,
    search: str = "",
    skip: int = 0,
    limit: int = 5,
) -> list:
    """Lấy danh sách phiên phân trang. Lỗi trả []."""
    try:
        params = {"skip": skip, "limit": limit}
        if search.strip():
            params["search"] = search.strip()

        res = session.get(
            f"{API_BASE_URL}/history/sessions",
            headers=get_auth_headers(),
            params=params,
        )
        if res.status_code == 200:
            return res.json()
        logger.warning(f"get_history failed: {res.status_code}")
        return []
    except requests.RequestException as exc:
        logger.warning(f"get_history error: {exc}")
        return []


def get_history_summary(session: requests.Session, search: str = "") -> dict:
    """Tóm tắt phiên và sự kiện. Lỗi trả {}."""
    try:
        params = {}
        if search.strip():
            params["search"] = search.strip()
        res = session.get(
            f"{API_BASE_URL}/history/summary",
            params=params,
            headers=get_auth_headers(),
        )
        if res.status_code == 200:
            return res.json()
        logger.warning(f"get_history_summary failed: {res.status_code}")
        return {}
    except requests.RequestException as exc:
        logger.warning(f"get_history_summary error: {exc}")
        return {}


def get_session_detail(session: requests.Session, session_id: int) -> dict | None:
    """Chi tiết phiên kèm sự kiện. Lỗi trả None."""
    try:
        res = session.get(
            f"{API_BASE_URL}/history/session/{session_id}",
            headers=get_auth_headers(),
        )
        if res.status_code == 200:
            return res.json()
        logger.warning(f"get_session_detail failed: {res.status_code}")
        return None
    except requests.RequestException as exc:
        logger.warning(f"get_session_detail error: {exc}")
        return None


def get_all_sessions(session: requests.Session) -> list:
    """Lấy toàn bộ phiên (không phân trang). Lỗi trả []."""
    try:
        res = session.get(
            f"{API_BASE_URL}/history/sessions",
            headers=get_auth_headers(),
            params={"skip": 0, "limit": 100},
        )
        if res.status_code == 200:
            return res.json()
        logger.warning(f"get_all_sessions failed: {res.status_code}")
        return []
    except requests.RequestException as exc:
        logger.warning(f"get_all_sessions error: {exc}")
        return []


def delete_session(session: requests.Session, session_id: int):
    """Xóa phiên. Trả response thô, lỗi kết nối trả None."""
    try:
        return session.delete(
            f"{API_BASE_URL}/history/session/{session_id}",
            headers=get_auth_headers(),
        )
    except requests.RequestException as exc:
        logger.warning(f"delete_session error: {exc}")
        return None
