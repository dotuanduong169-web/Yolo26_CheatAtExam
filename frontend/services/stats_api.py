"""Lớp gọi API thống kê: số liệu theo ngày.
Luồng chính: trang thống kê gọi hàm này rồi vẽ biểu đồ."""

import logging

import requests

from config import API_BASE_URL
from utils.http import get_auth_headers

logger = logging.getLogger(__name__)


def get_daily_stats(session: requests.Session) -> list:
    """Lấy thống kê hằng ngày từ backend. Lỗi thì trả [] ."""
    try:
        res = session.get(
            f"{API_BASE_URL}/stats/daily",
            headers=get_auth_headers(),
        )
        if res.status_code == 200:
            return res.json()
        logger.warning(f"get_daily_stats failed: {res.status_code}")
        return []
    except requests.RequestException as exc:
        logger.warning(f"get_daily_stats error: {exc}")
        return []
