"""Hàng tab điều hướng ngang dưới header: luôn thấy, bấm để chuyển trang."""

import streamlit as st

TABS = [
    ("home", "🎥 Giám sát", "pages/home.py"),
    ("events", "🚨 Sự kiện", "pages/events.py"),
    ("statistics", "📊 Thống kê", "pages/statistics.py"),
    ("history", "🕘 Lịch sử", "pages/history.py"),
    ("devices", "📷 Thiết bị", "pages/devices.py"),
    ("setting", "⚙️ Cài đặt", "pages/setting.py"),
]


def render_nav_tabs(active: str = "home") -> None:
    """Vẽ hàng tab ngang. Tab đang mở tô đậm, các tab còn lại bấm để chuyển."""
    cols = st.columns(len(TABS))
    for i, (key, label, target) in enumerate(TABS):
        with cols[i]:
            if key == active:
                st.markdown(
                    f"<div class='nav-tab-active'>{label}</div>",
                    unsafe_allow_html=True,
                )
            elif st.button(label, key=f"navtab_{key}", use_container_width=True):
                st.switch_page(target)

    st.markdown(
        """
        <style>
        .nav-tab-active {
            text-align: center;
            padding: 8px 4px;
            border-radius: 10px;
            background-color: #1677ff;
            color: white;
            font-weight: 600;
            font-size: 14px;
        }
        div[data-testid="stButton"] > button[kind="secondary"] {
            border-radius: 10px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
