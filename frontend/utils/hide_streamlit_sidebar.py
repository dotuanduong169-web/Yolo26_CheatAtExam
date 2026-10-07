"""Ẩn hoàn toàn sidebar bên trái của Streamlit để dùng thanh điều hướng ngang phía trên."""

import streamlit as st

_HIDE_CSS = """
<style>
[data-testid="stSidebar"], 
section[data-testid="stSidebar"], 
[data-testid="stSidebarNav"], 
[data-testid="collapsedControl"], 
[data-testid="stSidebarCollapsedControl"],
[data-testid="stSidebarCollapseButton"],
[data-testid="stSidebarHeader"],
[data-testid="stSidebarUserContent"],
button[kind="header"] {
    display: none !important;
    width: 0 !important;
    min-width: 0 !important;
    max-width: 0 !important;
    height: 0 !important;
    visibility: hidden !important;
    pointer-events: none !important;
    position: absolute !important;
    left: -9999px !important;
    margin: 0 !important;
    padding: 0 !important;
    border: none !important;
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

