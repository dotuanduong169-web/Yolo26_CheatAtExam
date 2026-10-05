"""Hệ thống thông báo đồng bộ toàn diện: Toast nổi góc trên-phải chuẩn Enterprise & Inline Alert nội tuyến đồng bộ."""

import streamlit as st

_CSS = """
<style>
/* ==========================================================================
   TOAST NOTIFICATION (NỔI GÓC TRÊN-PHẢI DÓNG THẲNG HÀNG CONTAINER 1280px)
   ========================================================================== */
.sys-toast-wrap {
    position: fixed !important;
    right: max(24px, calc((100vw - 1280px) / 2 + 24px)) !important;
    z-index: 1000005 !important;
    pointer-events: auto !important;
    display: flex !important;
    flex-direction: column !important;
    align-items: flex-end !important;
}

/* Hàng đợi toast: render tập trung ở top-level (header) nên toast không bao giờ
   nằm trong dialog/modal — luôn đúng vị trí góc trên-phải hệ thống */

.sys-toast {
    display: flex !important;
    align-items: flex-start !important;
    gap: 12px !important;
    width: 360px !important;
    max-width: calc(100vw - 32px) !important;
    padding: 12px 14px !important;
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 10px !important;
    box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.08), 0 4px 6px -2px rgba(0, 0, 0, 0.04) !important;
    overflow: hidden !important;
    position: relative !important;
    animation: sys-toast-slide 4.5s cubic-bezier(0.16, 1, 0.3, 1) forwards !important;
    backdrop-filter: blur(12px) !important;
    cursor: pointer !important;
    user-select: none !important;
}

.sys-toast.success { border-left: 4px solid #16a34a !important; }
.sys-toast.error   { border-left: 4px solid #dc2626 !important; }
.sys-toast.warning { border-left: 4px solid #d97706 !important; }
.sys-toast.info    { border-left: 4px solid #2563eb !important; }

.sys-toast-icon-box {
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    width: 28px !important;
    height: 28px !important;
    min-width: 28px !important;
    min-height: 28px !important;
    border-radius: 50% !important;
    flex-shrink: 0 !important;
    margin-top: 1px !important;
}

.sys-toast.success .sys-toast-icon-box { background: #f0fdf4 !important; color: #16a34a !important; }
.sys-toast.error .sys-toast-icon-box   { background: #fef2f2 !important; color: #dc2626 !important; }
.sys-toast.warning .sys-toast-icon-box { background: #fffbeb !important; color: #d97706 !important; }
.sys-toast.info .sys-toast-icon-box    { background: #eff6ff !important; color: #2563eb !important; }

.sys-toast-body {
    flex: 1 1 0% !important;
    display: flex !important;
    flex-direction: column !important;
    gap: 3px !important;
    padding-right: 18px !important;
}

.sys-toast-title {
    font-size: 11px !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.5px !important;
    line-height: 1.25 !important;
}

.sys-toast.success .sys-toast-title { color: #15803d !important; }
.sys-toast.error .sys-toast-title   { color: #b91c1c !important; }
.sys-toast.warning .sys-toast-title { color: #b45309 !important; }
.sys-toast.info .sys-toast-title    { color: #1d4ed8 !important; }

.sys-toast-msg {
    font-size: 13px !important;
    font-weight: 500 !important;
    color: #1e293b !important;
    line-height: 1.4 !important;
    word-break: break-word !important;
}

/* Nút tắt Toast */
.sys-toast-close {
    position: absolute !important;
    top: 10px !important;
    right: 10px !important;
    width: 20px !important;
    height: 20px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    color: #94a3b8 !important;
    cursor: pointer !important;
    border-radius: 4px !important;
    transition: all 0.15s ease !important;
}

.sys-toast-close:hover {
    background: #f1f5f9 !important;
    color: #475569 !important;
}

/* Thanh đếm ngược tiến trình ở chân Toast */
.sys-toast-progress {
    position: absolute !important;
    bottom: 0 !important;
    left: 0 !important;
    height: 2.5px !important;
    width: 100% !important;
    transform-origin: left !important;
    animation: sys-toast-bar 4.5s linear forwards !important;
}

.sys-toast.success .sys-toast-progress { background: #16a34a !important; }
.sys-toast.error .sys-toast-progress   { background: #dc2626 !important; }
.sys-toast.warning .sys-toast-progress { background: #d97706 !important; }
.sys-toast.info .sys-toast-progress    { background: #2563eb !important; }

.sys-toast:hover {
    box-shadow: 0 14px 28px -4px rgba(0, 0, 0, 0.12), 0 6px 10px -2px rgba(0, 0, 0, 0.06) !important;
}

.sys-toast:hover,
.sys-toast:hover .sys-toast-progress {
    animation-play-state: paused !important;
}

@media (max-width: 768px) {
    .sys-toast-wrap {
        right: 16px !important;
        left: 16px !important;
        align-items: stretch !important;
    }
    .sys-toast {
        width: 100% !important;
        max-width: 100% !important;
    }
}

@keyframes sys-toast-slide {
    0% {
        opacity: 0;
        transform: translateX(36px) scale(0.96);
    }
    8% {
        opacity: 1;
        transform: translateX(0) scale(1);
    }
    88% {
        opacity: 1;
        transform: translateX(0) scale(1);
    }
    100% {
        opacity: 0;
        transform: translateY(-8px) scale(0.96);
        pointer-events: none;
    }
}

@keyframes sys-toast-bar {
    0% { transform: scaleX(1); }
    100% { transform: scaleX(0); }
}

/* ==========================================================================
   INLINE ALERT (THÔNG BÁO NỘI TUYẾN ĐỒNG BỘ CARD 10px TRONG TRANG & DIALOG)
   ========================================================================== */
.sys-inline-alert {
    display: flex !important;
    align-items: flex-start !important;
    gap: 12px !important;
    padding: 12px 16px !important;
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 10px !important;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03) !important;
    margin: 8px 0 14px 0 !important;
    width: 100% !important;
    box-sizing: border-box !important;
}

.sys-inline-alert.success { border-left: 4px solid #16a34a !important; background: #fdfdfd !important; }
.sys-inline-alert.error   { border-left: 4px solid #dc2626 !important; background: #fdfdfd !important; }
.sys-inline-alert.warning { border-left: 4px solid #d97706 !important; background: #fdfdfd !important; }
.sys-inline-alert.info    { border-left: 4px solid #2563eb !important; background: #fdfdfd !important; }

.sys-inline-icon-box {
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    width: 28px !important;
    height: 28px !important;
    min-width: 28px !important;
    min-height: 28px !important;
    border-radius: 50% !important;
    flex-shrink: 0 !important;
    margin-top: 1px !important;
}

.sys-inline-alert.success .sys-inline-icon-box { background: #f0fdf4 !important; color: #16a34a !important; }
.sys-inline-alert.error .sys-inline-icon-box   { background: #fef2f2 !important; color: #dc2626 !important; }
.sys-inline-alert.warning .sys-inline-icon-box { background: #fffbeb !important; color: #d97706 !important; }
.sys-inline-alert.info .sys-inline-icon-box    { background: #eff6ff !important; color: #2563eb !important; }

.sys-inline-body {
    flex: 1 1 0% !important;
    display: flex !important;
    flex-direction: column !important;
    gap: 2px !important;
}

.sys-inline-title {
    font-size: 11.5px !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.5px !important;
    line-height: 1.3 !important;
}

.sys-inline-alert.success .sys-inline-title { color: #15803d !important; }
.sys-inline-alert.error .sys-inline-title   { color: #b91c1c !important; }
.sys-inline-alert.warning .sys-inline-title { color: #b45309 !important; }
.sys-inline-alert.info .sys-inline-title    { color: #1d4ed8 !important; }

.sys-inline-msg {
    font-size: 13px !important;
    font-weight: 500 !important;
    color: #334155 !important;
    line-height: 1.45 !important;
}

/* ==========================================================================
   EMPTY STATE BANNER (KHỐI THÔNG BÁO RỖNG ĐỒNG BỘ TOÀN HỆ THỐNG)
   ========================================================================== */
.sys-empty-card {
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    justify-content: center !important;
    padding: 36px 20px !important;
    background: #ffffff !important;
    border: 1px dashed #cbd5e1 !important;
    border-radius: 10px !important;
    text-align: center !important;
    margin: 12px 0 20px 0 !important;
    gap: 8px !important;
}

.sys-empty-icon {
    width: 44px !important;
    height: 44px !important;
    border-radius: 50% !important;
    background: #f1f5f9 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    color: #64748b !important;
    margin-bottom: 4px !important;
}

.sys-empty-title {
    font-size: 14px !important;
    font-weight: 600 !important;
    color: #334155 !important;
}

.sys-empty-desc {
    font-size: 12.5px !important;
    color: #64748b !important;
    max-width: 440px !important;
    line-height: 1.4 !important;
}
</style>
"""

_ICONS = {
    "success": (
        '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">'
        '  <polyline points="20 6 9 17 4 12"/>'
        '</svg>'
    ),
    "error": (
        '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">'
        '  <circle cx="12" cy="12" r="10"/>'
        '  <line x1="12" y1="8" x2="12" y2="12"/>'
        '  <line x1="12" y1="16" x2="12.01" y2="16"/>'
        '</svg>'
    ),
    "warning": (
        '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">'
        '  <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>'
        '  <line x1="12" y1="9" x2="12" y2="13"/>'
        '  <line x1="12" y1="17" x2="12.01" y2="17"/>'
        '</svg>'
    ),
    "info": (
        '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">'
        '  <circle cx="12" cy="12" r="10"/>'
        '  <line x1="12" y1="16" x2="12" y2="12"/>'
        '  <line x1="12" y1="8" x2="12.01" y2="8"/>'
        '</svg>'
    ),
}

_TITLES = {
    "success": "Thành công",
    "error": "Lỗi hệ thống",
    "warning": "Cảnh báo",
    "info": "Thông báo",
}


def _show_toast(kind: str, msg: str, title: str | None = None) -> None:
    """Hiện toast thông báo cao cấp, cố định góc trên-phải dưới thanh điều hướng.
    Luôn cùng một vị trí để không nhảy lung tung giữa các lần rerun."""
    top = 118
    title_text = title or _TITLES.get(kind, "Thông báo")
    icon_svg = _ICONS.get(kind, "")

    toast_html = (
        _CSS
        + f"<div class='sys-toast-wrap' style='top:{top}px;' onclick='this.remove();'>"
        + f"  <div class='sys-toast {kind}'>"
        + f"    <div class='sys-toast-icon-box'>{icon_svg}</div>"
        + f"    <div class='sys-toast-body'>"
        + f"      <div class='sys-toast-title'>{title_text}</div>"
        + f"      <div class='sys-toast-msg'>{msg}</div>"
        + f"    </div>"
        + f"    <div class='sys-toast-close' onclick='this.closest(\".sys-toast-wrap\").remove(); event.stopPropagation();' title='Đóng'>"
        + f"      <svg width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'><line x1='18' y1='6' x2='6' y2='18'></line><line x1='6' y1='6' x2='18' y2='18'></line></svg>"
        + f"    </div>"
        + f"    <div class='sys-toast-progress'></div>"
        + f"  </div>"
        + f"</div>"
    )
    st.markdown(toast_html, unsafe_allow_html=True)


def _show_inline(kind: str, msg: str, title: str | None = None) -> None:
    """Hiện thông báo nội tuyến dạng Card bo góc 10px đồng bộ, nằm ngay trong vị trí trang/dialog."""
    title_text = title or _TITLES.get(kind, "Thông báo")
    icon_svg = _ICONS.get(kind, "")

    alert_html = (
        _CSS
        + f"<div class='sys-inline-alert {kind}'>"
        + f"  <div class='sys-inline-icon-box'>{icon_svg}</div>"
        + f"  <div class='sys-inline-body'>"
        + f"    <div class='sys-inline-title'>{title_text}</div>"
        + f"    <div class='sys-inline-msg'>{msg}</div>"
        + f"  </div>"
        + f"</div>"
    )
    st.markdown(alert_html, unsafe_allow_html=True)


def _show_empty(title: str, desc: str | None = None) -> None:
    """Hiện khối thông báo trạng thái rỗng (empty state) bo góc 10px đồng bộ."""
    desc_html = f"<div class='sys-empty-desc'>{desc}</div>" if desc else ""
    empty_html = (
        _CSS
        + "<div class='sys-empty-card'>"
        + "  <div class='sys-empty-icon'>"
        + "    <svg width='22' height='22' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z'></path><polyline points='3.27 6.96 12 12.01 20.73 6.96'></polyline><line x1='12' y1='22.08' x2='12' y2='12'></line></svg>"
        + "  </div>"
        + f"  <div class='sys-empty-title'>{title}</div>"
        + f"  {desc_html}"
        + "</div>"
    )
    st.markdown(empty_html, unsafe_allow_html=True)


def _enqueue(kind: str, msg: str, title: str | None = None) -> None:
    """Xếp toast vào hàng đợi, tối đa 3 cái mới nhất (tránh spam sau nhiều rerun)."""
    queue = st.session_state.get("_toast_queue", [])
    queue.append({"kind": kind, "msg": msg, "title": title})
    st.session_state["_toast_queue"] = queue[-3:]


def flush() -> None:
    """Render toàn bộ toast đang xếp hàng tại vị trí gọi (top-level).
    Gọi trong render_page_header và cuối login.py để toast luôn neo ngoài,
    đúng góc trên-phải hệ thống kể cả khi hành động xảy ra trong dialog."""
    queue = st.session_state.pop("_toast_queue", [])
    for item in queue:
        _show_toast(item["kind"], item["msg"], item.get("title"))


class _Notify:
    """Facade gọi toast notification hoặc inline alert đồng bộ toàn hệ thống."""

    # ── Toast Notifications (Nổi góc trên-phải) ─────────────────
    # success/error/warning/info: render NGAY, chỉ dùng ở luồng page-level
    # (ngoài dialog). Trong dialog: defer_* nếu sau đó rerun/switch,
    # inline_* nếu ở lại dialog không rerun.
    def success(self, msg: str, title: str | None = None) -> None:
        _show_toast("success", msg, title)

    def error(self, msg: str, title: str | None = None) -> None:
        _show_toast("error", msg, title)

    def warning(self, msg: str, title: str | None = None) -> None:
        _show_toast("warning", msg, title)

    def info(self, msg: str, title: str | None = None) -> None:
        _show_toast("info", msg, title)

    # ── Deferred Toasts (hiện sau rerun/switch, tại header trang mới) ──
    def defer_success(self, msg: str, title: str | None = None) -> None:
        _enqueue("success", msg, title)

    def defer_error(self, msg: str, title: str | None = None) -> None:
        _enqueue("error", msg, title)

    def defer_warning(self, msg: str, title: str | None = None) -> None:
        _enqueue("warning", msg, title)

    def defer_info(self, msg: str, title: str | None = None) -> None:
        _enqueue("info", msg, title)

    # ── Inline Alerts (Hiển thị ngay trong trang / dialog) ───────
    def inline(self, msg: str, kind: str = "info", title: str | None = None) -> None:
        _show_inline(kind, msg, title)

    def inline_info(self, msg: str, title: str | None = None) -> None:
        _show_inline("info", msg, title)

    def inline_warning(self, msg: str, title: str | None = None) -> None:
        _show_inline("warning", msg, title)

    def inline_error(self, msg: str, title: str | None = None) -> None:
        _show_inline("error", msg, title)

    def inline_success(self, msg: str, title: str | None = None) -> None:
        _show_inline("success", msg, title)

    # ── Empty State Card (Trạng thái rỗng) ───────────────────────
    def empty_state(self, title: str, desc: str | None = None) -> None:
        _show_empty(title, desc)


notify = _Notify()
