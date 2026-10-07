"""Nạp file CSS bọc trong thẻ style để tiêm vào Streamlit."""

import streamlit as st
from pathlib import Path

# Thư mục gốc frontend (chứa styles/), neo theo vị trí file này để
# chạy đúng dù khởi động Streamlit từ root hay từ frontend/
FRONTEND_ROOT = Path(__file__).resolve().parents[1]


@st.cache_resource(show_spinner=False)
def _read_css_cached(abs_path: str) -> str:
    """Đọc nội dung file CSS 1 lần, giữ trong resource cache (tránh I/O mỗi rerun)."""
    with open(abs_path, encoding="utf-8") as f:
        return f.read()


def load_css(file_path: str) -> str:
    """Đọc file CSS và bọc trong thẻ <style>."""
    path = Path(file_path)
    if not path.is_absolute():
        path = FRONTEND_ROOT / file_path
    return f"<style>{_read_css_cached(str(path))}</style>"
