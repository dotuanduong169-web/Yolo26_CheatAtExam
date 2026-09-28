"""Bảo vệ trang: chưa đăng nhập thì chuyển về login."""

import requests
import streamlit as st

from config import API_BASE_URL


def require_auth() -> None:
    """Kiểm tra token còn hiệu lực qua /users/profile. Hết hạn thì về login."""
    if "client" not in st.session_state:
        st.session_state.client = requests.Session()

    if not st.session_state.get("access_token_value"):
        st.switch_page("pages/login.py")
        st.stop()

    try:
        from utils.http import get_auth_headers

        res = st.session_state.client.get(
            f"{API_BASE_URL}/users/profile",
            headers=get_auth_headers(),
            timeout=5,
        )
        if res.status_code != 200:
            st.error("Phiên đăng nhập hết hạn")
            st.switch_page("pages/login.py")
            st.stop()
    except requests.RequestException:
        st.error("Lỗi kết nối server")
        st.switch_page("pages/login.py")
        st.stop()
