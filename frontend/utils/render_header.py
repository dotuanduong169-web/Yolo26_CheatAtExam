import streamlit as st
from utils.load_css import load_css


def render_page_header(title: str, active: str | None = None):
    """Vẽ thanh header chung: logo ExamCheat AI + tiêu đề trang.
    active: key trang hiện tại (home/events/statistics/history/devices/setting)
    để vẽ hàng tab điều hướng ngay dưới header.
    """
    st.markdown(load_css("styles/header.css"), unsafe_allow_html=True)
    st.markdown(load_css("styles/app_theme.css"), unsafe_allow_html=True)

    session_id = st.session_state.get("session_id")
    is_running = st.session_state.get("running", False)
    user_name = st.session_state.get("user_fullname") or st.session_state.get("username") or "Cán bộ coi thi"
    role_raw = st.session_state.get("user_role", "teacher")
    role_label = "Quản trị viên" if role_raw == "admin" else "Cán bộ coi thi"

    if is_running and session_id:
        session_text = f"Phòng #{session_id}"
        session_badge_cls = "online"
        session_badge_text = "Đang giám sát"
    else:
        session_text = "Chưa mở ca thi"
        session_badge_cls = ""
        session_badge_text = "Hệ thống sẵn sàng"

    header_html = (
        '<div class="global-top-bar">'
        '  <div class="top-logo-section">'
        '    <div class="top-logo-box">'
        '      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">'
        '        <path d="M3 3v18h18" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
        '        <path d="M7 14l4-4 4 4 6-6" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
        '        <path d="M21 8v-4h-4" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
        '      </svg>'
        '    </div>'
        '    <div class="top-logo-text">'
        '      <div class="top-logo-main">ExamCheat AI</div>'
        '      <div class="top-logo-sub">Giám sát thi thông minh</div>'
        '    </div>'
        '  </div>'
        f'  <div class="top-page-title">{title}</div>'
        '  <div class="top-meta-right">'
        f'    <div>Ca thi: <strong>{session_text}</strong></div>'
        f'    <div>{role_label}: <strong>{user_name}</strong></div>'
        f'    <div>Trạng thái: <span class="badge {session_badge_cls}">{session_badge_text}</span></div>'
        '    <a href="/login" class="header-logout-btn" onclick="try{window.parent.localStorage.removeItem(\'examcheat_auth\');}catch(e){};try{localStorage.removeItem(\'examcheat_auth\');}catch(e){};" title="Đăng xuất khỏi hệ thống">'
        '      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '        <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>'
        '        <polyline points="16 17 21 12 16 7"/>'
        '        <line x1="21" y1="12" x2="9" y2="12"/>'
        '      </svg>'
        '      <span>Đăng xuất</span>'
        '    </a>'
        '  </div>'
        '</div>'
    )
    st.markdown(header_html, unsafe_allow_html=True)

    if active:
        from components.nav_tabs import render_nav_tabs
        render_nav_tabs(active)
