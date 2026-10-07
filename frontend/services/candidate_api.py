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


def open_session(session: requests.Session, session_id: int):
    """Mở ca thi để thí sinh vào thi online. Trả response thô."""
    try:
        return session.post(
            f"{API_BASE_URL}/candidates/session/{session_id}/open",
            headers=get_auth_headers(),
        )
    except requests.RequestException as exc:
        logger.warning(f"open_session error: {exc}")
        return None


def close_session(session: requests.Session, session_id: int):
    """Kết thúc ca thi online. Trả response thô."""
    try:
        return session.post(
            f"{API_BASE_URL}/candidates/session/{session_id}/close",
            headers=get_auth_headers(),
        )
    except requests.RequestException as exc:
        logger.warning(f"close_session error: {exc}")
        return None


def create_online_session(session: requests.Session, phong_thi: str, mon_thi: str):
    """Tạo mới ca thi online. Trả response thô."""
    try:
        return session.post(
            f"{API_BASE_URL}/candidates/session/create",
            json={"PhongThi": phong_thi, "MonThi": mon_thi},
            headers=get_auth_headers(),
        )
    except requests.RequestException as exc:
        logger.warning(f"create_online_session error: {exc}")
        return None


def get_candidate_snapshot(session: requests.Session, session_id: int) -> bytes | None:
    """Tải ảnh snapshot mới nhất của thí sinh. Trả bytes nếu có, None nếu chưa có ảnh."""
    try:
        res = session.get(
            f"{API_BASE_URL}/candidates/session/{session_id}/snapshot",
            headers=get_auth_headers(),
            timeout=3,
        )
        if res.status_code == 200:
            return res.content
        return None
    except Exception as exc:
        logger.debug(f"get_candidate_snapshot error: {exc}")
        return None


def extract_error_detail(resp: requests.Response | None, default: str = "Thao tác thất bại") -> str:
    """Bóc tách thông báo lỗi chi tiết từ HTTP response hoặc lỗi kết nối."""
    if resp is None:
        return "Không thể kết nối đến máy chủ Backend (vui lòng kiểm tra tiến trình Backend trên cổng 8000)."
    if resp.status_code == 404:
        return (
            "API chưa sẵn sàng (HTTP 404). Backend uvicorn đang chạy mã cũ, "
            "vui lòng khởi động lại backend để nạp các endpoint mới."
        )
    if resp.status_code == 401:
        return "Phiên làm việc đã hết hạn (HTTP 401). Vui lòng đăng nhập lại."
    if resp.status_code == 403:
        return "Bạn không có quyền thực hiện thao tác này (HTTP 403)."
    try:
        data = resp.json()
        if isinstance(data, dict):
            detail = data.get("detail") or data.get("message")
            if detail:
                return str(detail)
    except Exception:
        pass
    text = (resp.text or "").strip()
    if text and len(text) < 120 and "<html" not in text.lower():
        return f"{default}: {text}"
    return f"{default} (Mã lỗi HTTP: {resp.status_code})"
