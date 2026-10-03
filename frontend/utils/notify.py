"""Thông báo thống nhất toàn hệ thống: góc trên-phải, tự ẩn sau vài giây."""

import uuid

import streamlit as st

_CSS = """
<style>
.sys-toast-wrap { position: fixed; top: 76px; right: 16px; z-index: 1000001; pointer-events: none; }
.sys-toast {
    display: flex; align-items: center; gap: 8px;
    min-width: 240px; max-width: 360px;
    margin-bottom: 8px; padding: 10px 14px;
    border-radius: 10px; font-size: 13px; font-weight: 600; color: #fff;
    box-shadow: 0 4px 16px rgba(0,0,0,0.18);
    animation: sys-toast-life 4s ease forwards;
}
.sys-toast.success { background: #16a34a; }
.sys-toast.error { background: #dc2626; }
.sys-toast.warning { background: #d97706; }
.sys-toast.info { background: #2563eb; }
@keyframes sys-toast-life {
    0% { opacity: 0; transform: translateX(30px); }
    8% { opacity: 1; transform: translateX(0); }
    80% { opacity: 1; transform: translateX(0); }
    100% { opacity: 0; transform: translateX(30px); }
}
</style>
"""

_ICONS = {"success": "", "error": "", "warning": "", "info": ""}


def _show(kind: str, msg: str) -> None:
    """Hiện một toast góc trên-phải, xếp chồng bằng offset theo số lượng."""
    n = st.session_state.get("_toast_n", 0)
    st.session_state["_toast_n"] = (n + 1) % 6
    top = 76 + (n % 6) * 62
    st.markdown(
        _CSS
        + f"<div class='sys-toast-wrap' style='top:{top}px'>"
        + f"<div class='sys-toast {kind}'>{_ICONS[kind]}<span>{msg}</span></div>"
        + "</div>",
        unsafe_allow_html=True,
    )


class _Notify:
    """Facade gọi notify.success/error/warning/info."""

    def success(self, msg: str) -> None:
        _show("success", msg)

    def error(self, msg: str) -> None:
        _show("error", msg)

    def warning(self, msg: str) -> None:
        _show("warning", msg)

    def info(self, msg: str) -> None:
        _show("info", msg)


notify = _Notify()
