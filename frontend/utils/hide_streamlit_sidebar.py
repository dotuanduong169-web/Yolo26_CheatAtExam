"""Ẩn thanh điều hướng mặc định của Streamlit để dùng sidebar riêng.
Luồng chính: bơm CSS ẩn khối stSidebarNav -> gọi ở đầu mỗi trang."""

import streamlit as st

_HIDE_CSS = """
<style>
[data-testid="stSidebarNav"] {display: none;}
</style>
"""


def hide_sidebar() -> None:
    """Bơm CSS để ẩn thanh điều hướng mặc định của Streamlit."""
    st.markdown(_HIDE_CSS, unsafe_allow_html=True)