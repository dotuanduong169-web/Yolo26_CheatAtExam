"""Trang đăng nhập: xác thực và lưu token.
Luồng chính: nhập email/mật khẩu -> gọi API login -> lưu token vào cookie và session -> chuyển trang giám sát."""

import streamlit as st
from streamlit_cookies_manager import EncryptedCookieManager

from config import COOKIE_PASSWORD
from services.auth_api import login
from utils.http import init_session_state
from utils.load_css import load_css

# ── Cấu hình trang ────────────────────────────────────────
st.set_page_config(layout="centered", initial_sidebar_state="collapsed", page_title="Đăng nhập")

init_session_state()

cookies = EncryptedCookieManager(password=COOKIE_PASSWORD)
if not cookies.ready():
    st.stop()

# Ẩn sidebar + mọi kiểu dáng nằm trong login.css
try:
    st.markdown(load_css("styles/login.css"), unsafe_allow_html=True)
except Exception:
    pass

# ── Băng tiêu đề ──────────────────────────────────────────
st.markdown("""
<div class="login-banner">
    <div class="logo-box">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M3 3v18h18" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M7 14l4-4 4 4 6-6" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M21 8v-4h-4" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
    </div>
    <div class="logo-text">EduVision AI</div>
</div>
<div class="welcome-title">Chào mừng trở lại</div>
""", unsafe_allow_html=True)

# ── Biểu mẫu đăng nhập ────────────────────────────────────
email = st.text_input("Email", placeholder="email@truong.edu.vn")
password = st.text_input("Mật khẩu", type="password", placeholder="Nhập mật khẩu")

st.markdown('<div id="forgot-password-marker"></div>', unsafe_allow_html=True)
if st.button("Quên mật khẩu?"):
    st.info("Tính năng đang phát triển")

if st.button("Đăng nhập", type="primary", use_container_width=True):
    if not email or not password:
        st.error("❌ Vui lòng nhập đầy đủ email và mật khẩu")
    else:
        with st.spinner("Đang kiểm tra..."):
            res = login(st.session_state.client, email, password)

        if res.status_code == 200:
            data = res.json()
            access_token = data.get("access_token")
            refresh_token = data.get("refresh_token")

            if access_token:
                # Lưu token vào cookie để giữ đăng nhập
                cookies["access_token"] = access_token
                if refresh_token:
                    cookies["refresh_token"] = refresh_token
                cookies.save()

                # Lưu token vào session để dùng trong phiên này
                st.session_state["access_token_value"] = access_token
                st.session_state["refresh_token_value"] = refresh_token
                st.session_state["user_role"] = data.get("role", "teacher")
                st.session_state["is_login"] = True

                # Gắn token lên HTTP client để gọi API
                st.session_state.client.cookies.set("access_token", access_token)
                if refresh_token:
                    st.session_state.client.cookies.set("refresh_token", refresh_token)

                st.success("✅ Đăng nhập thành công")
                st.switch_page("pages/home.py")

        elif res.status_code == 401:
            st.error("❌ Email hoặc mật khẩu không chính xác")
        else:
            st.error(f"❌ Lỗi: {res.text}")

# ── Chân trang dẫn sang đăng ký ───────────────────────────
st.markdown("""
<div class="register-footer">
    <span class="text-muted">Chưa có tài khoản?</span> 
    <a href="register" target="_self" class="register-link">Đăng ký ngay</a>
</div>
""", unsafe_allow_html=True)