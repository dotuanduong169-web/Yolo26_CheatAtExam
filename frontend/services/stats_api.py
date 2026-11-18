"""Gọi API thống kê: theo ngày."""

import logging

import requests

from config import API_BASE_URL
from utils.http import cache_get, cache_set, get_auth_headers

logger = logging.getLogger(__name__)


def get_daily_stats(session: requests.Session, days: int = 30) -> list:
    """Lấy thống kê theo ngày. Lỗi trả []."""
    try:
        res = session.get(
            f"{API_BASE_URL}/stats/daily",
            params={"days": days},
            headers=get_auth_headers(),
        )
        if res.status_code == 200:
            return res.json()
        logger.warning(f"get_daily_stats failed: {res.status_code}")
        return []
    except requests.RequestException as exc:
        logger.warning(f"get_daily_stats error: {exc}")
        return []


def get_stats_summary(session: requests.Session) -> dict:
    """Lấy tóm tắt thống kê toàn hệ thống."""
    hit, val = cache_get("stats:summary", 20)
    if hit:
        return val
    try:
        res = session.get(
            f"{API_BASE_URL}/stats/summary",
            headers=get_auth_headers(),
        )
        if res.status_code == 200:
            data = res.json()
            cache_set("stats:summary", data)
            return data
        logger.warning(f"get_stats_summary failed: {res.status_code}")
        return {}
    except requests.RequestException as exc:
        logger.warning(f"get_stats_summary error: {exc}")
        return {}


def get_stats_by_date(session: requests.Session, days: int = 30) -> list:
    """Lấy số lượt phát hiện vi phạm theo từng ngày."""
    try:
        res = session.get(
            f"{API_BASE_URL}/stats/by-date",
            params={"days": days},
            headers=get_auth_headers(),
        )
        if res.status_code == 200:
            return res.json()
        logger.warning(f"get_stats_by_date failed: {res.status_code}")
        return []
    except requests.RequestException as exc:
        logger.warning(f"get_stats_by_date error: {exc}")
        return []


def get_weekly_stats(session: requests.Session, weeks: int = 4) -> list:
    """Lấy thống kê xu hướng theo tuần."""
    try:
        res = session.get(
            f"{API_BASE_URL}/stats/weekly",
            params={"weeks": weeks},
            headers=get_auth_headers(),
        )
        if res.status_code == 200:
            return res.json()
        logger.warning(f"get_weekly_stats failed: {res.status_code}")
        return []
    except requests.RequestException as exc:
        logger.warning(f"get_weekly_stats error: {exc}")
        return []


def get_behavior_distribution(session: requests.Session) -> list:
    """Lấy phân bố hành vi vi phạm thực tế từ backend."""
    hit, val = cache_get("stats:distr", 20)
    if hit:
        return val
    try:
        res = session.get(
            f"{API_BASE_URL}/stats/distribution",
            headers=get_auth_headers(),
        )
        if res.status_code == 200:
            data = res.json()
            cache_set("stats:distr", data)
            return data
        logger.warning(f"get_behavior_distribution failed: {res.status_code}")
        return []
    except requests.RequestException as exc:
        logger.warning(f"get_behavior_distribution error: {exc}")
        return []


def _clean_params(**kwargs) -> dict:
    """Bỏ tham số None/rỗng trước khi gọi API."""
    return {k: v for k, v in kwargs.items() if v not in (None, "", [])}


def get_stats_overview(
    session: requests.Session,
    session_id: int | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
) -> dict:
    """KPI thống kê gắn thí sinh. Lỗi trả {}."""
    params = _clean_params(session_id=session_id, from_date=from_date, to_date=to_date)
    key = f"stats:overview:{params}"
    hit, val = cache_get(key, 10)
    if hit:
        return val
    try:
        res = session.get(
            f"{API_BASE_URL}/stats/overview",
            params=params,
            headers=get_auth_headers(),
        )
        if res.status_code == 200:
            data = res.json()
            cache_set(key, data)
            return data
        logger.warning(f"get_stats_overview failed: {res.status_code}")
        return {}
    except requests.RequestException as exc:
        logger.warning(f"get_stats_overview error: {exc}")
        return {}


def get_candidate_stats(
    session: requests.Session,
    session_id: int | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
) -> list:
    """Tổng hợp cảnh báo theo từng thí sinh. Lỗi trả []."""
    params = _clean_params(session_id=session_id, from_date=from_date, to_date=to_date)
    key = f"stats:candidates:{params}"
    hit, val = cache_get(key, 10)
    if hit:
        return val
    try:
        res = session.get(
            f"{API_BASE_URL}/stats/candidates",
            params=params,
            headers=get_auth_headers(),
        )
        if res.status_code == 200:
            data = res.json()
            cache_set(key, data)
            return data
        logger.warning(f"get_candidate_stats failed: {res.status_code}")
        return []
    except requests.RequestException as exc:
        logger.warning(f"get_candidate_stats error: {exc}")
        return []


def get_timeline(
    session: requests.Session,
    session_id: int | None = None,
    candidate_id: int | None = None,
    only_alerts: bool = True,
    from_date: str | None = None,
    to_date: str | None = None,
    skip: int = 0,
    limit: int = 30,
) -> dict:
    """Timeline cảnh báo của tất cả thí sinh, kèm ảnh base64. Lỗi trả {}."""
    params = _clean_params(
        session_id=session_id,
        candidate_id=candidate_id,
        only_alerts="true" if only_alerts else "false",
        from_date=from_date,
        to_date=to_date,
        skip=skip,
        limit=limit,
    )
    key = f"stats:timeline:{params}"
    hit, val = cache_get(key, 6)
    if hit:
        return val
    try:
        res = session.get(
            f"{API_BASE_URL}/stats/timeline",
            params=params,
            headers=get_auth_headers(),
            timeout=15,
        )
        if res.status_code == 200:
            data = res.json()
            cache_set(key, data)
            return data
        logger.warning(f"get_timeline failed: {res.status_code}")
        return {}
    except requests.RequestException as exc:
        logger.warning(f"get_timeline error: {exc}")
        return {}


