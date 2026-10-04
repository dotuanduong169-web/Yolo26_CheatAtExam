"""Thanh tab điều hướng: 1 widget segmented duy nhất, DOM giống hệt mọi trang.
Cố định vị trí, dàn đều 100% theo chiều ngang, cách nhau ra cân đối.
Nút đăng xuất đã được chuyển lên góc phải thanh Header.
"""

import streamlit as st

OPTIONS = [
    "Giám sát",
    "Sự kiện",
    "Thống kê",
    "Lịch sử",
    "Thiết bị",
    "Cài đặt",
]

TARGETS = {
    "Giám sát": "pages/home.py",
    "Sự kiện": "pages/events.py",
    "Thống kê": "pages/statistics.py",
    "Lịch sử": "pages/history.py",
    "Thiết bị": "pages/devices.py",
    "Cài đặt": "pages/users.py",
}

DEFAULTS = {
    "home": "Giám sát",
    "events": "Sự kiện",
    "statistics": "Thống kê",
    "history": "Lịch sử",
    "devices": "Thiết bị",
    "setting": "Cài đặt",
}


def render_nav_tabs(active: str = "home") -> None:
    """Vẽ thanh tab điều hướng dàn đều toàn màn hình."""
    st.markdown(
        """
        <style>
        div.element-container:has(div[data-testid="stSegmentedControl"]) {
            position: sticky !important;
            top: 60px !important;
            z-index: 999 !important;
            background: #f8fafc !important;
            padding: 8px 0 6px 0 !important;
            margin-bottom: 2px !important;
        }
        div[data-testid="stSegmentedControl"] {
            width: 100% !important;
            max-width: 100% !important;
            background: #ffffff !important;
            border: 1px solid #e2e8f0 !important;
            border-radius: 10px !important;
            padding: 4px !important;
            display: flex !important;
            box-shadow: 0 1px 3px rgba(0,0,0,0.03) !important;
        }
        div[data-testid="stSegmentedControl"] > div {
            width: 100% !important;
            display: flex !important;
            gap: 8px !important;
        }
        div[data-testid="stSegmentedControl"] button {
            flex: 1 1 0px !important;
            min-width: 0 !important;
            border-radius: 7px !important;
            font-weight: 500 !important;
            font-size: 13.5px !important;
            height: 36px !important;
            padding: 0 8px !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            border: 1px solid transparent !important;
            color: #475569 !important;
            background: transparent !important;
            transition: all 0.15s ease-in-out !important;
        }
        div[data-testid="stSegmentedControl"] button:hover {
            background-color: #f1f5f9 !important;
            color: #0f172a !important;
        }
        div[data-testid="stSegmentedControl"] button[aria-checked="true"] {
            background-color: #eff6ff !important;
            color: #2563eb !important;
            border-color: #bfdbfe !important;
            font-weight: 600 !important;
            box-shadow: 0 1px 2px rgba(37,99,235,0.08) !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    sel = st.segmented_control(
        "Điều hướng",
        options=OPTIONS,
        default=DEFAULTS.get(active, OPTIONS[0]),
        label_visibility="collapsed",
        key=f"navtabs_{active}",
    )

    current = DEFAULTS.get(active)
    if sel and sel != current and sel in TARGETS:
        st.switch_page(TARGETS[sel])
