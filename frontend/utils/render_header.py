import streamlit as st
from utils.load_css import load_css

def render_page_header(title: str):
    """Vẽ thanh header chung: logo ExamCheat AI + tiêu đề trang + thông tin phiên & giám thị."""
    st.markdown(load_css("styles/header.css"), unsafe_allow_html=True)
    st.markdown(load_css("styles/app_theme.css"), unsafe_allow_html=True)

    # Lấy thông tin phiên & người dùng từ session_state nếu có
    session_id = st.session_state.get("session_id")
    is_running = st.session_state.get("running", False)
    user_name = st.session_state.get("user_fullname") or st.session_state.get("username") or "Cán bộ coi thi"
    role_label = "Admin" if st.session_state.get("user_role") == "admin" else "Giám thị"

    session_text = f"Phòng: #{session_id}" if (is_running and session_id) else "Chưa mở phiên"
    session_badge_cls = "online" if is_running else ""
    session_badge_text = "Đang chạy" if is_running else "Chờ khởi tạo"

    st.markdown(f"""
    <div class="global-top-bar">
        <div class="top-logo-section">
            <div class="top-logo-box">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M3 3v18h18" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    <path d="M7 14l4-4 4 4 6-6" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    <path d="M21 8v-4h-4" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
            </div>
            <div class="top-logo-text">
                <div class="top-logo-main">ExamCheat AI</div>
                <div class="top-logo-sub">YOLO26 Edge Detection</div>
            </div>
        </div>
        <div class="top-page-title">{title}</div>
        <div class="top-meta-right">
            <div>Phiên thi: <strong>{session_text}</strong></div>
            <div>{role_label}: <strong>{user_name}</strong></div>
            <div>Thiết bị: <span class="badge {session_badge_cls}">Edge AI ({session_badge_text})</span></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

