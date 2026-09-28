"""Trang đăng nhập."""

import streamlit as st

from services.auth_api import login
from utils.http import init_session_state
from utils.load_css import load_css

# ── Config ──────────────────────────────────────────────────
st.set_page_config(layout="centered", initial_sidebar_state="collapsed", page_title="Đăng nhập")

init_session_state()

try:
    st.markdown(load_css("styles/login.css"), unsafe_allow_html=True)
except Exception:
    pass

# ── Header Banner ───────────────────────────────────────────
st.markdown("""
<div class="login-banner">
    <div class="logo-box">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M3 3v18h18" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M7 14l4-4 4 4 6-6" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M21 8v-4h-4" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
    </div>
    <div class="logo-text">ExamCheat AI</div>
</div>
<div class="welcome-title">Chào mừng trở lại</div>
""", unsafe_allow_html=True)

# ── Form ────────────────────────────────────────────────────
username = st.text_input("Tên đăng nhập", placeholder="Nhập tên đăng nhập")
password = st.text_input("Mật khẩu", type="password", placeholder="Nhập mật khẩu")

st.markdown('<div id="forgot-password-marker"></div>', unsafe_allow_html=True)
if st.button("Quên mật khẩu?"):
    st.info("Tính năng đang phát triển")

if st.button("Đăng nhập", type="primary", use_container_width=True):
    if not username or not password:
        st.error("❌ Vui lòng nhập đầy đủ tên đăng nhập và mật khẩu")
    else:
        with st.spinner("Đang kiểm tra..."):
            res = login(st.session_state.client, username, password)

        if res is None:
            st.error("❌ Không kết nối được server")
        elif res.status_code == 200:
            data = res.json()
            st.session_state["access_token_value"] = data.get("access_token")
            st.session_state["refresh_token_value"] = data.get("refresh_token")
            st.session_state["user_role"] = data.get("role", "teacher")
            st.session_state["is_login"] = True
            st.success("✅ Đăng nhập thành công")
            st.switch_page("pages/home.py")
        elif res.status_code == 401:
            st.error("❌ Tên đăng nhập hoặc mật khẩu không chính xác")
        else:
            st.error(f"❌ Lỗi: {res.text}")

# ── Footer ──────────────────────────────────────────────────
st.markdown("""
<div class="register-footer">
    <span class="text-muted">Chưa có tài khoản?</span> 
    <a href="register" target="_self" class="register-link">Đăng ký ngay</a>
</div>
""", unsafe_allow_html=True)
