"""Trang đăng ký tài khoản mới kèm kiểm tra độ mạnh mật khẩu.
Luồng chính: nhập thông tin -> kiểm tra hợp lệ -> gọi API register -> chuyển trang đăng nhập."""

import base64
from pathlib import Path
import streamlit as st

from services.auth_api import register
from utils.http import init_session_state
from utils.load_css import load_css

# ── Khởi tạo ──────────────────────────────────────────────
init_session_state()

st.set_page_config(layout="centered", initial_sidebar_state="collapsed", page_title="Đăng ký")

st.markdown(load_css("styles/register.css"), unsafe_allow_html=True)

def get_base64_image(image_path):
    """Đọc ảnh từ đĩa và đổi sang chuỗi base64 để nhúng vào trang."""
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()

promo_image_path = Path(__file__).parent.parent / "assets" / "promo_ai.png"
if promo_image_path.exists():
    promo_src = f"data:image/png;base64,{get_base64_image(str(promo_image_path))}"
else:
    promo_src = "https://images.unsplash.com/photo-1620712943543-bcc4688e7485?auto=format&fit=crop&w=800&q=80"


col_left, col_right = st.columns([1.1, 1])

# ── Cột trái (quảng bá) ───────────────────────────────────
with col_left:
    st.markdown('<div id="left-column-marker"></div>', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="logo-row">
        <svg fill="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
            <path d="M12 3L1 9L4 10.636V17C4 18.1046 7.58172 19 12 19C16.4183 19 20 18.1046 20 17V10.636L23 9L12 3ZM20.25 9L12 13.4862L3.75 9L12 4.51382L20.25 9ZM18 17C18 17.5523 15.3137 18 12 18C8.68629 18 6 17.5523 6 17V11.727L11.5126 14.7214C11.8153 14.8858 12.1847 14.8858 12.4874 14.7214L18 11.727V17Z"></path>
        </svg>
        <span class="logo-text">EduVision AI</span>
    </div>
    
    <div class="promo-image-box">
        <!-- Đặt link ảnh nền ở dòng dưới đây (thay thế thuộc tính src) -->
        <img src="{promo_src}" alt="Promo">
    </div>
    
    <h2 class="promo-title">Kiến tạo tương lai cùng <span class="highlight">Trí tuệ Nhân tạo</span></h2>
    <p class="promo-subtitle">Tham gia cộng đồng học tập thông minh nhất hiện nay.</p>
    """, unsafe_allow_html=True)

# ── Cột phải (biểu mẫu) ───────────────────────────────────
with col_right:
    st.markdown('<div id="right-column-marker"></div>', unsafe_allow_html=True)
    st.markdown("""
    <h2 class="form-title">Tạo tài khoản mới</h2>
    <p class="form-subtitle">Bắt đầu hành trình học tập của bạn chỉ trong vài phút.</p>
    """, unsafe_allow_html=True)

    name = st.text_input("Họ và Tên", placeholder="Nguyễn Văn A")
    email = st.text_input("Email", placeholder="example@email.com")
    
    col_pw, col_conf = st.columns(2)
    with col_pw:
        password = st.text_input("Mật khẩu", type="password", placeholder="********")
    with col_conf:
        confirm = st.text_input("Xác nhận", type="password", placeholder="********")

    # Chỉ báo độ mạnh mật khẩu
    if password:
        if len(password) < 6:
            st.warning("🔴 Mật khẩu phải ít nhất 6 ký tự")
        elif not any(c.isupper() for c in password):
            st.warning("🟡 Mật khẩu phải chứa ít nhất 1 ký tự in hoa")
        elif not any(c.isdigit() for c in password):
            st.warning("🟡 Mật khẩu phải chứa ít nhất 1 chữ số")
        else:
            st.success("🟢 Mật khẩu mạnh")

    if st.button("Đăng ký tài khoản", type="primary", use_container_width=True):
        # Kiểm tra dữ liệu nhập trước khi gọi API
        if not name or not email or not password or not confirm:
            st.error("❌ Vui lòng nhập đầy đủ thông tin")
        elif password != confirm:
            st.error("❌ Mật khẩu không khớp")
        elif len(password) < 6:
            st.error("❌ Mật khẩu phải ít nhất 6 ký tự")
        elif not any(c.isupper() for c in password):
            st.error("❌ Mật khẩu phải chứa ít nhất 1 ký tự in hoa")
        elif not any(c.isdigit() for c in password):
            st.error("❌ Mật khẩu phải chứa ít nhất 1 chữ số")
        else:
            with st.spinner("Đang đăng ký..."):
                res = register(st.session_state.client, name, email, password)

                if res.status_code == 200:
                    st.success("✅ Đăng ký thành công! Vui lòng đăng nhập")
                    st.switch_page("pages/login.py")
                elif res.status_code == 409:
                    st.error("❌ Email này đã được đăng ký")
                elif res.status_code == 429:
                    detail = "Quá nhiều yêu cầu đăng ký"
                    try:
                        detail = res.json().get("detail", detail)
                    except Exception:
                        pass
                    st.error(f"🔒 {detail}")
                elif res.status_code == 422:
                    st.error("❌ Dữ liệu không hợp lệ")
                else:
                    detail = res.text
                    try:
                        detail = res.json().get("detail", detail)
                    except Exception:
                        pass
                    st.error(f"❌ Lỗi: {detail}")

    st.markdown("""
    <div class="login-footer">
        <span class="text-muted">Đã có tài khoản?</span>
        <a href="login" target="_self" class="login-link">Đăng nhập ngay</a>
    </div>
    """, unsafe_allow_html=True)
