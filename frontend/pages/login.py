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
        st.error("Vui lòng nhập đầy đủ tên đăng nhập và mật khẩu")
    else:
        with st.spinner("Đang kiểm tra..."):
            res = login(st.session_state.client, username, password)

        if res is None:
            st.error("Không kết nối được đến máy chủ hoặc máy chủ không phản hồi (hết thời gian chờ).")
        elif res.status_code == 200:
            data = res.json()
            tok = data.get("access_token")
            role = data.get("role", "teacher")
            st.session_state["access_token_value"] = tok
            st.session_state["refresh_token_value"] = data.get("refresh_token")
            st.session_state["user_role"] = role
            st.session_state["username"] = username
            st.session_state["is_login"] = True

            # Lưu vào query params để giữ phiên khi F5 / Refresh trang
            if tok:
                st.query_params["auth"] = tok
                st.query_params["role"] = role
                st.query_params["u"] = username

            # Lấy họ tên hiển thị
            try:
                from services.user_api import get_user
                profile = get_user(st.session_state.client)
                if profile:
                    st.session_state["user_fullname"] = profile.get("HoVaTen")
            except Exception:
                pass

            st.success("Đăng nhập thành công")
            st.switch_page("pages/home.py")

        elif res.status_code in (401, 403):
            detail_msg = ""
            try:
                detail_msg = str(res.json().get("detail", ""))
            except Exception:
                pass
            if "locked" in detail_msg.lower() or "khóa" in detail_msg.lower():
                st.error("Tài khoản của bạn đã bị khóa. Vui lòng liên hệ quản trị viên.")
            else:
                st.error("Tên đăng nhập hoặc mật khẩu không chính xác")
        else:
            st.error(f"Lỗi đăng nhập: {res.text}")

st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
col_demo1, col_demo2 = st.columns(2)
with col_demo1:
    if st.button("Vào nhanh (Admin Demo)", use_container_width=True):
        st.session_state["access_token_value"] = "demo_token_admin"
        st.session_state["user_role"] = "admin"
        st.session_state["username"] = "admin_duong"
        st.session_state["user_fullname"] = "Đỗ Tuấn Dương"
        st.session_state["is_login"] = True
        st.query_params["auth"] = "demo_token_admin"
        st.query_params["role"] = "admin"
        st.query_params["u"] = "admin_duong"
        st.switch_page("pages/home.py")

with col_demo2:
    if st.button("Vào nhanh (Giám thị Demo)", use_container_width=True):
        st.session_state["access_token_value"] = "demo_token_teacher"
        st.session_state["user_role"] = "teacher"
        st.session_state["username"] = "gv_le_ngoc_an"
        st.session_state["user_fullname"] = "ThS. Lê Ngọc An"
        st.session_state["is_login"] = True
        st.query_params["auth"] = "demo_token_teacher"
        st.query_params["role"] = "teacher"
        st.query_params["u"] = "gv_le_ngoc_an"
        st.switch_page("pages/home.py")

