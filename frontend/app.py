"""Điểm vào ứng dụng: kiểm tra đăng nhập rồi định tuyến trang."""

import requests
import streamlit as st

from config import API_BASE_URL

# ── HTTP Client ─────────────────────────────────────────────
if "client" not in st.session_state:
    st.session_state.client = requests.Session()

# ── Validate Session ────────────────────────────────────────
is_login = False

if st.session_state.get("access_token_value"):
    try:
        res = st.session_state.client.get(
            f"{API_BASE_URL}/users/profile",
            headers={"Authorization": f"Bearer {st.session_state['access_token_value']}"},
            timeout=5,
        )
        is_login = res.status_code == 200
    except requests.RequestException:
        is_login = False

# ── Route ───────────────────────────────────────────────────
if is_login:
    st.switch_page("pages/home.py")
else:
    st.switch_page("pages/login.py")
