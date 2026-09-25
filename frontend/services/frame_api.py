"""Lớp gọi API khung hình: danh sách frame, chi tiết frame, kết quả phân tích.
Luồng chính: trang home/session_analysis/frame_detail gọi hàm này kèm token."""

import logging

import requests

from config import API_BASE_URL
from utils.http import get_auth_headers

logger = logging.getLogger(__name__)


def get_frames_by_session(session: requests.Session, session_id: int) -> list:
    """Lấy mọi khung hình đã trích xuất của một phiên. Lỗi thì trả [] ."""
    try:
        res = session.get(
            f"{API_BASE_URL}/frames/{session_id}",
            headers=get_auth_headers(),
        )
        if res.status_code == 200:
            return res.json()
        logger.warning(f"get_frames_by_session failed: {res.status_code}")
        return []
    except requests.RequestException as exc:
        logger.warning(f"get_frames_by_session error: {exc}")
        return []


def get_frame_detail(session: requests.Session, frame_id: int) -> dict | None:
    """Lấy dữ liệu phát hiện chi tiết của một khung hình. Lỗi thì trả None."""
    try:
        res = session.get(
            f"{API_BASE_URL}/frames/detail/{frame_id}",
            headers=get_auth_headers(),
        )
        if res.status_code == 200:
            return res.json()
        logger.warning(f"get_frame_detail failed: {res.status_code}")
        return None
    except requests.RequestException as exc:
        logger.warning(f"get_frame_detail error: {exc}")
        return None


def get_frame_analysis(session: requests.Session, session_id: int) -> list:
    """Lấy kết quả phân tích (số ca tập trung/buồn ngủ) của mọi frame trong phiên."""
    try:
        res = session.get(
            f"{API_BASE_URL}/frames/analysis/{session_id}",
            headers=get_auth_headers(),
        )
        if res.status_code == 200:
            return res.json()
        logger.warning(f"get_frame_analysis failed: {res.status_code}")
        return []
    except requests.RequestException as exc:
        logger.warning(f"get_frame_analysis error: {exc}")
        return []
