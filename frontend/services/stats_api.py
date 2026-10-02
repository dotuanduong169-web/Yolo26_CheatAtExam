"""Gọi API thống kê: theo ngày."""

import logging

import requests

from config import API_BASE_URL
from utils.http import get_auth_headers

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
    try:
        res = session.get(
            f"{API_BASE_URL}/stats/summary",
            headers=get_auth_headers(),
        )
        if res.status_code == 200:
            return res.json()
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
    try:
        res = session.get(
            f"{API_BASE_URL}/stats/distribution",
            headers=get_auth_headers(),
        )
        if res.status_code == 200:
            return res.json()
        logger.warning(f"get_behavior_distribution failed: {res.status_code}")
        return []
    except requests.RequestException as exc:
        logger.warning(f"get_behavior_distribution error: {exc}")
        return []


