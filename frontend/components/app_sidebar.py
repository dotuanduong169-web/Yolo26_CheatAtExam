"""Thanh sidebar: menu điều hướng và đăng xuất."""

import streamlit as st
from services.auth_api import logout

def render_sidebar(active: str = "home") -> None:
    """Vẽ sidebar, highlight mục đang mở. Thứ tự nút phải khớp CSS nth-child."""
    with st.sidebar:
        st.markdown('<div style="height: 10px;"></div>', unsafe_allow_html=True)

        btn_home = st.button("🎥 Giám sát", key="nav_home", use_container_width=True)
        btn_events = st.button("🚨 Sự kiện", key="nav_events", use_container_width=True)
        btn_stats = st.button("📊 Thống kê", key="nav_statistics", use_container_width=True)
        btn_hist = st.button("🕘 Lịch sử", key="nav_history", use_container_width=True)
        btn_devices = st.button("📷 Thiết bị", key="nav_devices", use_container_width=True)
        btn_settings = st.button("⚙️ Cài đặt", key="nav_setting", use_container_width=True)

        if btn_home: st.switch_page("pages/home.py")
        if btn_events: st.switch_page("pages/events.py")
        if btn_stats: st.switch_page("pages/statistics.py")
        if btn_hist: st.switch_page("pages/history.py")
        if btn_devices: st.switch_page("pages/devices.py")
        if btn_settings: st.switch_page("pages/setting.py")

        menu_map = {"home": 1, "events": 2, "statistics": 3, "history": 4, "devices": 5, "setting": 6}
        active_idx = menu_map.get(active, 1)

        st.markdown(f"""
        <style>
        section[data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div:nth-child({active_idx + 1}) button {{
            background-color: #1677ff !important;
            color: white !important;
            font-weight: 600 !important;
            box-shadow: 0 4px 12px rgba(22, 119, 255, 0.2) !important;
        }}
        section[data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div:nth-child({active_idx + 1}) button p {{
            color: white !important;
        }}
        </style>
        """, unsafe_allow_html=True)

        if st.button("↪️ Đăng xuất", key="logout_btn", use_container_width=True):
            try:
                if "client" in st.session_state:
                    logout(st.session_state.client)
            except Exception:
                pass
            st.session_state.clear()
            st.switch_page("pages/login.py")
