"""Thanh sidebar: menu điều hướng và đăng xuất."""

import streamlit as st

def render_sidebar(active: str = "home") -> None:
    """Vẽ sidebar, highlight mục đang mở. Thứ tự nút phải khớp CSS nth-child."""
    with st.sidebar:
        st.markdown('<div style="height: 10px;"></div>', unsafe_allow_html=True)

        btn_home = st.button("Giám sát trực tiếp", key="nav_home", use_container_width=True)
        btn_events = st.button("Sự kiện phát hiện", key="nav_events", use_container_width=True)
        btn_devices = st.button("Thiết bị biên", key="nav_devices", use_container_width=True)
        btn_stats = st.button("Báo cáo thống kê", key="nav_statistics", use_container_width=True)
        btn_users = st.button("Quản lý người dùng", key="nav_users", use_container_width=True)

        if btn_home: st.switch_page("pages/home.py")
        if btn_events: st.switch_page("pages/events.py")
        if btn_devices: st.switch_page("pages/devices.py")
        if btn_stats: st.switch_page("pages/statistics.py")
        if btn_users: st.switch_page("pages/users.py")

        menu_map = {"home": 1, "events": 2, "devices": 3, "statistics": 4, "users": 5, "setting": 5}
        active_idx = menu_map.get(active, 1)

        st.markdown(f"""
        <style>
        section[data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div:nth-child({active_idx + 1}) button {{
            background-color: #2563eb !important;
            color: white !important;
            font-weight: 600 !important;
            border-radius: 4px !important;
        }}
        section[data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div:nth-child({active_idx + 1}) button p {{
            color: white !important;
        }}
        </style>
        """, unsafe_allow_html=True)
