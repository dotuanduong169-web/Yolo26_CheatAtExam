"""Gọi API thí sinh thi online: nhập danh sách, liệt kê, lưới giám thị."""

import logging

import requests

from config import API_BASE_URL
from utils.http import get_auth_headers

logger = logging.getLogger(__name__)


def import_candidates(session: requests.Session, session_id: int, candidates: list):
    """Nhập danh sách thí sinh (SBD, họ tên, lớp) cho ca thi. Trả response thô."""
    try:
        return session.post(
            f"{API_BASE_URL}/candidates/import",
            json={"FK_MaPhienGiamSat": session_id, "candidates": candidates},
            headers=get_auth_headers(),
        )
    except requests.RequestException as exc:
        logger.warning(f"import_candidates error: {exc}")
        return None


def list_candidates(session: requests.Session, session_id: int) -> list:
    """Liệt kê thí sinh của ca thi. Lỗi trả []."""
    try:
        res = session.get(
            f"{API_BASE_URL}/candidates",
            params={"session_id": session_id},
            headers=get_auth_headers(),
        )
        if res.status_code == 200:
            return res.json()
        logger.warning(f"list_candidates failed: {res.status_code}")
        return []
    except requests.RequestException as exc:
        logger.warning(f"list_candidates error: {exc}")
        return []


def exam_overview(session: requests.Session, session_id: int) -> list:
    """Lưới giám thị: trạng thái từng thí sinh. Lỗi trả []."""
    try:
        res = session.get(
            f"{API_BASE_URL}/candidates/overview",
            params={"session_id": session_id},
            headers=get_auth_headers(),
        )
        if res.status_code == 200:
            return res.json()
        logger.warning(f"exam_overview failed: {res.status_code}")
        return []
    except requests.RequestException as exc:
        logger.warning(f"exam_overview error: {exc}")
        return []
