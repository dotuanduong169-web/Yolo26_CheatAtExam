import requests
import streamlit as st

from config import API_BASE_URL
from utils.http import init_session_state

st.set_page_config(layout="wide", initial_sidebar_state="collapsed", page_title="ExamCheat AI")

# ── Khôi phục session & HTTP Client ─────────────────────────
init_session_state()

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
