"""Chặn trang khi chưa đăng nhập: đưa người dùng về trang login.
Luồng chính: khôi phục token từ cookie -> gắn vào client -> kiểm tra /users/profile."""

import requests
import streamlit as st
from streamlit_cookies_manager import EncryptedCookieManager

from config import API_BASE_URL, COOKIE_PASSWORD


def require_auth() -> None:
    """Kiểm tra đã đăng nhập chưa.
    Khôi phục token từ cookie vào HTTP client rồi đối chiếu với backend.
    Thất bại thì chuyển về trang đăng nhập."""
    cookies = EncryptedCookieManager(password=COOKIE_PASSWORD)
    if not cookies.ready():
        st.stop()

    if "client" not in st.session_state:
        st.session_state.client = requests.Session()

    client = st.session_state.client

    access_token = cookies.get("access_token")
    refresh_token = cookies.get("refresh_token")

    if access_token:
        client.cookies.set("access_token", access_token)
    if refresh_token:
        client.cookies.set("refresh_token", refresh_token)

    if not access_token:
        st.error("Please log in to continue")
        st.switch_page("pages/login.py")
        st.stop()

    try:
        res = client.get(f"{API_BASE_URL}/users/profile", timeout=5)
        if res.status_code != 200:
            cookies.clear()
            st.error("Session expired")
            st.switch_page("pages/login.py")
            st.stop()
    except requests.RequestException:
        st.error("Connection error")
        st.switch_page("pages/login.py")
        st.stop()