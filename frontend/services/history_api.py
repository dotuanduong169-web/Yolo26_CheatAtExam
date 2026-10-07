"""Gọi API lịch sử: danh sách phiên, tóm tắt, chi tiết, xóa phiên."""

import logging

import requests

from config import API_BASE_URL
from utils.http import cache_get, cache_invalidate, cache_set, get_auth_headers

logger = logging.getLogger(__name__)


def get_history(
    session: requests.Session,
    search: str = "",
    skip: int = 0,
    limit: int = 5,
) -> list:
    """Lấy danh sách phiên phân trang. Lỗi trả []."""
    key = f"hist:list:{search.strip()}:{skip}:{limit}"
    hit, val = cache_get(key, 10)
    if hit:
        return val
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
            data = res.json()
            cache_set(key, data)
            return data
        logger.warning(f"get_history failed: {res.status_code}")
        return []
    except requests.RequestException as exc:
        logger.warning(f"get_history error: {exc}")
        return []


def get_history_summary(session: requests.Session, search: str = "", *args, **kwargs) -> dict:
    """Tóm tắt phiên và sự kiện. Lỗi trả {}."""
    key = f"hist:summary:{search.strip() if isinstance(search, str) else ''}"
    hit, val = cache_get(key, 10)
    if hit:
        return val
    try:
        params = {}
        if isinstance(search, str) and search.strip():
            params["search"] = search.strip()
        res = session.get(
            f"{API_BASE_URL}/history/summary",
            params=params,
            headers=get_auth_headers(),
        )
        if res.status_code == 200:
            data = res.json()
            cache_set(key, data)
            return data
        logger.warning(f"get_history_summary failed: {res.status_code}")
        return {}
    except requests.RequestException as exc:
        logger.warning(f"get_history_summary error: {exc}")
        return {}


def get_session_detail(session: requests.Session, session_id: int) -> dict | None:
    """Chi tiết phiên kèm sự kiện. Lỗi trả None."""
    key = f"hist:detail:{session_id}"
    hit, val = cache_get(key, 10)
    if hit:
        return val
    try:
        res = session.get(
            f"{API_BASE_URL}/history/session/{session_id}",
            headers=get_auth_headers(),
        )
        if res.status_code == 200:
            data = res.json()
            cache_set(key, data)
            return data
        logger.warning(f"get_session_detail failed: {res.status_code}")
        return None
    except requests.RequestException as exc:
        logger.warning(f"get_session_detail error: {exc}")
        return None


def get_all_sessions(session: requests.Session) -> list:
    """Lấy toàn bộ phiên (không phân trang). Lỗi trả []."""
    hit, val = cache_get("hist:all100", 15)
    if hit:
        return val
    try:
        res = session.get(
            f"{API_BASE_URL}/history/sessions",
            headers=get_auth_headers(),
            params={"skip": 0, "limit": 100},
        )
        if res.status_code == 200:
            data = res.json()
            cache_set("hist:all100", data)
            return data
        logger.warning(f"get_all_sessions failed: {res.status_code}")
        return []
    except requests.RequestException as exc:
        logger.warning(f"get_all_sessions error: {exc}")
        return []


def delete_session(session: requests.Session, session_id: int):
    """Xóa phiên. Trả response thô, lỗi kết nối trả None."""
    try:
        res = session.delete(
            f"{API_BASE_URL}/history/session/{session_id}",
            headers=get_auth_headers(),
        )
        if res is not None and res.status_code == 200:
            cache_invalidate("hist:")
            cache_invalidate("ev:")
        return res
    except requests.RequestException as exc:
        logger.warning(f"delete_session error: {exc}")
        return None
