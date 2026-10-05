"""Helper HTTP dùng chung: header auth, wrapper an toàn, khởi tạo session state."""

import requests
import streamlit as st

from config import API_BASE_URL


# ── Session State Defaults ──────────────────────────────────

_DEFAULTS = {
    "is_login": False,
    "access_token_value": None,
    "refresh_token_value": None,
    "running": False,
    "session_id": None,
    "event_id": None,
    "selected_session": None,
    "capture_start_time": None,
    "refresh_key": 0,
    "page_loaded": "",
    "user_role": "teacher",
}


def init_session_state() -> None:
    """Đảm bảo mọi key session state tồn tại với giá trị mặc định và khôi phục khi F5."""
    for key, value in _DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = value

    if "client" not in st.session_state:
        st.session_state.client = requests.Session()

    # Khôi phục phiên khi F5 (Refresh) từ query params
    if not st.session_state.get("access_token_value"):
        saved_auth = st.query_params.get("auth")
        if saved_auth:
            st.session_state["access_token_value"] = saved_auth
            st.session_state["is_login"] = True
            saved_role = st.query_params.get("role")
            if saved_role:
                st.session_state["user_role"] = saved_role
            saved_user = st.query_params.get("u")
            if saved_user:
                st.session_state["username"] = saved_user
                st.session_state["user_fullname"] = saved_user


# ── Auth Headers ────────────────────────────────────────────


def get_auth_headers() -> dict:
    """Dựng header Authorization từ token đã lưu."""
    token = st.session_state.get("access_token_value")
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}



# ── Safe HTTP Wrappers ──────────────────────────────────────


def safe_get(url: str, timeout: int = 5):
    """GET kèm auth. Lỗi kết nối trả None."""
    try:
        return st.session_state.client.get(
            url, headers=get_auth_headers(), timeout=timeout
        )
    except requests.RequestException:
        return None


def safe_post(url: str, params: dict = None, json: dict = None, timeout: int = 10):
    """POST kèm auth. Lỗi kết nối trả None."""
    try:
        return st.session_state.client.post(
            url, params=params, json=json,
            headers=get_auth_headers(), timeout=timeout,
        )
    except requests.RequestException:
        return None


def safe_put(url: str, json: dict = None, timeout: int = 10):
    """PUT kèm auth. Lỗi kết nối trả None."""
    try:
        return st.session_state.client.put(
            url, json=json, headers=get_auth_headers(), timeout=timeout,
        )
    except requests.RequestException:
        return None


def safe_patch(url: str, json: dict = None, timeout: int = 10):
    """PATCH kèm auth. Lỗi kết nối trả None."""
    try:
        return st.session_state.client.patch(
            url, json=json, headers=get_auth_headers(), timeout=timeout,
        )
    except requests.RequestException:
        return None


def safe_delete(url: str, timeout: int = 10):
    """DELETE kèm auth. Lỗi kết nối trả None."""
    try:
        return st.session_state.client.delete(
            url, headers=get_auth_headers(), timeout=timeout,
        )
    except requests.RequestException:
        return None


def auth_query_params() -> str:
    """Chuỗi query giữ phiên đăng nhập, gắn vào link HTML action.

    Link <a href> reload toàn trang (mất session_state); gắn sẵn token vào URL
    để require_auth khôi phục phiên, tránh bị đá về trang login hay mở tab mới
    do người dùng Ctrl+click. Chỉ dùng cho demo local (token đã nằm sẵn trong URL
    từ cơ chế giữ phiên hiện tại).
    """
    from urllib.parse import quote

    q = st.query_params
    auth = st.session_state.get("access_token_value") or q.get("auth", "")
    refresh = st.session_state.get("refresh_token_value") or q.get("refresh", "")
    role = st.session_state.get("user_role") or q.get("role", "")
    u = st.session_state.get("username") or q.get("u", "")
    parts = [
        f"auth={quote(str(auth), safe='')}",
        f"role={quote(str(role), safe='')}",
        f"u={quote(str(u), safe='')}",
    ]
    if refresh:
        parts.append(f"refresh={quote(str(refresh), safe='')}")
    return "&".join(parts)
