"""Ẩn thanh điều hướng mặc định của Streamlit."""

import streamlit as st

_HIDE_CSS = """
<style>
[data-testid="stSidebarNav"] {display: none;}
</style>
"""


def hide_sidebar() -> None:
    """Tiêm CSS ẩn điều hướng sidebar mặc định."""
    st.markdown(_HIDE_CSS, unsafe_allow_html=True)
