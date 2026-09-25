"""Hàm HTTP dùng chung cho các gọi API.
Luồng chính: khởi tạo session -> gắn token xác thực -> gọi GET/POST an toàn."""

import requests
import streamlit as st

from config import API_BASE_URL


# ── Giá trị mặc định cho session ──────────────────────────

_DEFAULTS = {
    "is_login": False,
    "access_token_value": None,
    "refresh_token_value": None,
    "running": False,
    "session_id": None,
    "frame_id": None,
    "capture_start_time": None,
    "refresh_key": 0,
    "page_loaded": "",
    "user_role": "teacher",
}


def init_session_state() -> None:
    """Tạo đủ khóa session còn thiếu với giá trị mặc định."""
    for key, value in _DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = value

    if "client" not in st.session_state:
        st.session_state.client = requests.Session()


# ── Tiêu đề xác thực ──────────────────────────────────────


def get_auth_headers() -> dict:
    """Dựng tiêu đề Authorization từ token đã lưu."""
    token = (
        st.session_state.get("access_token_value")
        or st.session_state.get("token")
    )
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}


# ── Hàm GET/POST an toàn ──────────────────────────────────


def safe_get(url: str, timeout: int = 5):
    """Gọi GET kèm token. Mất kết nối thì trả None."""
    try:
        return st.session_state.client.get(
            url, headers=get_auth_headers(), timeout=timeout
        )
    except requests.RequestException:
        return None


def safe_post(url: str, params: dict = None, json: dict = None, timeout: int = 10):
    """Gọi POST kèm token. Mất kết nối thì trả None."""
    try:
        return st.session_state.client.post(
            url, params=params, json=json,
            headers=get_auth_headers(), timeout=timeout,
        )
    except requests.RequestException:
        return None
