"""Lớp gọi API lịch sử: danh sách phiên, tóm tắt, chi tiết, xóa phiên.
Luồng chính: trang lịch sử/chi tiết phiên gọi hàm này để lấy dữ liệu phân trang."""

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
    """Lấy danh sách phiên có phân trang. Lỗi thì trả [] ."""
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


def get_history_summary(session: requests.Session) -> dict:
    """Lấy tổng số phiên và số phiên trong tháng. Lỗi thì trả {}."""
    try:
        res = session.get(
            f"{API_BASE_URL}/history/summary",
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
    """Lấy đầy đủ chi tiết một phiên kèm khung hình. Lỗi thì trả None."""
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
    """Lấy toàn bộ phiên (không phân trang). Lỗi thì trả [] ."""
    try:
        res = session.get(
            f"{API_BASE_URL}/history/sessions",
            headers=get_auth_headers(),
        )
        if res.status_code == 200:
            return res.json()
        logger.warning(f"get_all_sessions failed: {res.status_code}")
        return []
    except requests.RequestException as exc:
        logger.warning(f"get_all_sessions error: {exc}")
        return []


def delete_session(session: requests.Session, session_id: int):
    """Xóa một phiên theo mã. Mất kết nối thì trả None."""
    try:
        return session.delete(
            f"{API_BASE_URL}/history/session/{session_id}",
            headers=get_auth_headers(),
        )
    except requests.RequestException as exc:
        logger.warning(f"delete_session error: {exc}")
        return None