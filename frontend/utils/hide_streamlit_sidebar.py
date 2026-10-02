"""Ẩn hoàn toàn sidebar bên trái của Streamlit để dùng thanh điều hướng ngang phía trên."""

import streamlit as st

_HIDE_CSS = """
<style>
[data-testid="stSidebar"], section[data-testid="stSidebar"] {
    display: none !important;
    width: 0px !important;
}
[data-testid="stSidebarNav"] {
    display: none !important;
}
[data-testid="collapsedControl"] {
    display: none !important;
}
.main .block-container {
    padding-left: 2rem !important;
    padding-right: 2rem !important;
    max-width: 1400px !important;
    margin: 0 auto !important;
}
</style>
"""


def hide_sidebar() -> None:
    """Tiêm CSS ẩn hoàn toàn sidebar bên trái."""
    st.markdown(_HIDE_CSS, unsafe_allow_html=True)

