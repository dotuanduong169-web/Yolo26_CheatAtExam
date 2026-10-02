import streamlit as st
from services.event_api import get_system_notifications
from utils.load_css import load_css


def render_page_header(title: str, active: str | None = None):
    """Vẽ thanh header chung: logo ExamCheat AI + tiêu đề trang + thông báo hệ thống góc trên bên phải.
    active: key trang hiện tại (home/events/statistics/history/devices/setting)
    để vẽ hàng tab điều hướng ngay dưới header.
    """
    st.markdown(load_css("styles/header.css"), unsafe_allow_html=True)
    st.markdown(load_css("styles/app_theme.css"), unsafe_allow_html=True)

    client = st.session_state.get("client")
    session_id = st.session_state.get("session_id")
    is_running = st.session_state.get("running", False)
    user_name = st.session_state.get("user_fullname") or st.session_state.get("username") or "Cán bộ coi thi"
    role_raw = st.session_state.get("user_role", "teacher")
    role_label = "Quản trị viên" if role_raw == "admin" else "Cán bộ coi thi"

    # Đồng bộ thông báo hệ thống từ backend
    notif_data = {"total_pending": 0, "alerts": [], "active_session": None, "system_status": "online"}
    if client:
        try:
            notif_data = get_system_notifications(client)
        except Exception:
            pass

    st.session_state["system_notifications"] = notif_data
    unread_alerts = notif_data.get("total_pending", 0)

    # Lấy thông tin phòng thi từ active_session nếu có
    active_sess = notif_data.get("active_session")
    if active_sess:
        room_name = active_sess.get("room") or f"P.{active_sess.get('session_id')}"
        sess_num = active_sess.get("session_id")
        session_text = f"{room_name} (Ca #{sess_num})"
        session_badge_cls = "online"
        session_badge_text = "Đang giám sát"
    elif is_running and session_id:
        session_text = f"Phòng #{session_id}"
        session_badge_cls = "online"
        session_badge_text = "Đang giám sát"
    else:
        session_text = "Chưa mở ca thi"
        session_badge_cls = ""
        session_badge_text = "Hệ thống sẵn sàng"

    bell_badge_cls = "danger" if unread_alerts > 0 else ""
    bell_hint = f"Có {unread_alerts} vi phạm chờ xác minh" if unread_alerts > 0 else "Hệ thống bình thường, không có vi phạm mới"

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
                <div class="top-logo-sub">Giám sát thi thông minh</div>
            </div>
        </div>
        <div class="top-page-title">{title}</div>
        <div class="top-meta-right">
            <div>Ca thi: <strong>{session_text}</strong></div>
            <div>{role_label}: <strong>{user_name}</strong></div>
            <div>Trạng thái: <span class="badge {session_badge_cls}">{session_badge_text}</span></div>
            <div class="top-bell-box" title="{bell_hint}">
                <span class="top-bell-text">Thông báo</span>
                <span class="top-bell-badge {bell_badge_cls}">{unread_alerts}</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


    if active:
        from components.nav_tabs import render_nav_tabs
        render_nav_tabs(active)


