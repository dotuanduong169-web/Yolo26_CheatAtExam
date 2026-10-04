"""Trang Sự kiện: Tự động chuyển hướng sang Tab Nhật ký sự kiện trong Lịch sử giám sát."""

import streamlit as st

st.set_page_config(layout="wide", initial_sidebar_state="collapsed", page_title="Sự kiện phát hiện")

# Chuyển hướng sang trang history với tab events
st.query_params["tab"] = "events"
st.switch_page("pages/history.py")
