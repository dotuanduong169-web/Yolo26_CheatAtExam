"""Thanh tab điều hướng: 1 widget segmented duy nhất, DOM giống hệt mọi trang.
Điểm logic: cùng options, cùng thứ tự, cùng key-pattern nên vị trí/kích thước
không đổi khi chuyển trang; tab đang mở highlight xanh theo theme."""

import streamlit as st

OPTIONS = [
    "Giám sát",
    "Sự kiện",
    "Thống kê",
    "Lịch sử",
    "Thiết bị",
    "Cài đặt",
    "Đăng xuất",
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
    """Vẽ thanh tab. Tab trắng, tab đang mở xanh; đăng xuất nằm cuối cùng."""
    st.markdown(
        """
        <style>
        div[data-testid="stSegmentedControl"] {
            background: #ffffff;
            border: 1px solid #e8eaed;
            border-radius: 12px;
            padding: 6px 8px;
        }
        div[data-testid="stSegmentedControl"] button {
            border-radius: 8px !important;
            font-weight: 600 !important;
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
    if sel and sel != current:
        if sel == "Đăng xuất":
            from services.auth_api import logout

            try:
                if "client" in st.session_state:
                    logout(st.session_state.client)
            except Exception:
                pass
            st.session_state["access_token_value"] = None
            st.session_state["is_login"] = False
            for _k in ("auth", "refresh", "role", "u"):
                if _k in st.query_params:
                    del st.query_params[_k]
            st.switch_page("pages/login.py")
        else:
            st.switch_page(TARGETS[sel])
