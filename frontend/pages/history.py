# -*- coding: utf-8 -*-
"""Trang lịch sử phiên: tìm kiếm, phân trang và xóa phiên."""

import streamlit as st
from utils.notify import notify


from services.history_api import (
    delete_session,
    get_history,
    get_history_summary,
)
from utils.auth_guard import require_auth
from utils.hide_streamlit_sidebar import hide_sidebar
from utils.http import init_session_state
from utils.load_css import load_css
from utils.render_header import render_page_header
from utils.status_helpers import get_session_status_badge

# ── Config ──────────────────────────────────────────────────
st.set_page_config(layout="wide", initial_sidebar_state="collapsed", page_title="Lịch sử")

st.markdown(load_css("styles/sidebar.css"), unsafe_allow_html=True)
st.markdown(load_css("styles/app_theme.css"), unsafe_allow_html=True)
st.markdown(load_css("styles/history.css"), unsafe_allow_html=True)

init_session_state()
require_auth()
hide_sidebar()
render_page_header("Lịch sử giám sát", active="history")

PAGE_SIZE = 5


def _fetch_history(session, search: str = "", page: int = 1) -> dict | None:
    """Lấy danh sách phiên và tóm tắt qua service."""
    skip = (page - 1) * PAGE_SIZE
    sessions = get_history(session, search=search, skip=skip, limit=PAGE_SIZE)
    try:
        summary = get_history_summary(session, search=search)
    except TypeError:
        try:
            summary = get_history_summary(session)
        except Exception:
            summary = {}
    except Exception:
        summary = {}

    if sessions is None:
        return None
    if summary is None:
        summary = {}

    return {
        "sessions": sessions,
        "total_sessions": summary.get("tong_phien", 0),
        "total_events": summary.get("tong_su_kien", 0),
    }


def handle_delete(session_id: int) -> None:
    """Xóa phiên và hiện kết quả."""
    res = delete_session(st.session_state.client, session_id)
    if not res:
        notify.error("Không thể kết nối đến máy chủ.")
        return
    if res.status_code == 200:
        notify.success("Xóa phiên giám sát thành công.")
        st.rerun()
    elif res.status_code == 400:
        notify.error("Không thể xóa phiên đang diễn ra.")
    elif res.status_code == 404:
        notify.error("Không tìm thấy phiên giám sát.")
    else:
        notify.error(f"Lỗi hệ thống: {res.text}")


@st.dialog("Xác nhận xóa phiên giám sát")
def confirm_delete(session_id: int):
    notify.inline(
        "Bạn có chắc chắn muốn xóa phiên giám sát này không? Toàn bộ sự kiện và hình ảnh bằng chứng liên quan sẽ bị xóa vĩnh viễn khỏi hệ thống.",
        kind="warning",
        title="Cảnh báo xóa dữ liệu"
    )

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Hủy bỏ", use_container_width=True):
            st.rerun()
    with c2:
        if st.button("Xác nhận xóa", type="primary", use_container_width=True):
            handle_delete(session_id)


# ── Xử lý query params phân trang và xóa phiên ──────────────
if "p" in st.query_params:
    try:
        st.session_state.hist_page = max(1, int(st.query_params["p"]))
    except Exception:
        pass

if "confirm_delete" in st.query_params:
    try:
        target_sid = int(st.query_params["confirm_delete"])
        confirm_delete(target_sid)
    except Exception:
        pass

# ── Session state for pagination ────────────────────────────
if "hist_page" not in st.session_state:
    st.session_state.hist_page = 1
if "hist_search" not in st.session_state:
    st.session_state.hist_search = ""

# ── Load Data ───────────────────────────────────────────────
data = _fetch_history(
    st.session_state.client,
    search=st.session_state.hist_search,
    page=st.session_state.hist_page,
)
if not data:
    st.stop()

# ── Summary Cards ───────────────────────────────────────────
col_s1, col_s2 = st.columns(2)

with col_s1:
    st.markdown(f"""
    <div class="summary-card">
        <div class="label">TỔNG PHIÊN GIÁM SÁT</div>
        <div class="value">{data['total_sessions']:,}</div>
        <div class="trend up">Toàn bộ ca thi</div>
    </div>
    """, unsafe_allow_html=True)

with col_s2:
    st.markdown(f"""
    <div class="summary-card">
        <div class="label">TỔNG SỰ KIỆN GIAN LẬN</div>
        <div class="value">{data['total_events']:,}</div>
        <div class="trend neutral">Đã ghi nhận trong DB</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("")

# ── Search ──────────────────────────────────────────────────
search_val = st.text_input(
    "Tìm kiếm",
    value=st.session_state.hist_search,
    placeholder="Tìm kiếm theo phòng thi hoặc môn thi...",
    label_visibility="collapsed",
)

if search_val != st.session_state.hist_search:
    st.session_state.hist_search = search_val
    st.session_state.hist_page = 1
    st.rerun()

# ── Data ────────────────────────────────────────────────────
sessions = data["sessions"]
total_sessions_count = data["total_sessions"]
total_pages = max((total_sessions_count - 1) // PAGE_SIZE + 1, 1)

# Đảm bảo trang hiện tại hợp lệ
if st.session_state.hist_page > total_pages:
    st.session_state.hist_page = total_pages
current_page = st.session_state.hist_page

# ── Table ───────────────────────────────────────────────────
st.markdown('<div class="table-card" style="background:#ffffff; border:1px solid #e2e8f0; border-radius:10px; padding:16px; box-shadow:0 1px 3px rgba(0,0,0,0.03);">', unsafe_allow_html=True)

th_cols = st.columns([1.2, 3.4, 1.8, 1.4, 0.8, 1.0])
with th_cols[0]:
    st.markdown('<span style="font-size:11.5px; font-weight:700; color:#64748b; letter-spacing:0.5px;">MÃ PHIÊN</span>', unsafe_allow_html=True)
with th_cols[1]:
    st.markdown('<span style="font-size:11.5px; font-weight:700; color:#64748b; letter-spacing:0.5px;">PHÒNG / MÔN THI</span>', unsafe_allow_html=True)
with th_cols[2]:
    st.markdown('<span style="font-size:11.5px; font-weight:700; color:#64748b; letter-spacing:0.5px;">THỜI GIAN BẮT ĐẦU</span>', unsafe_allow_html=True)
with th_cols[3]:
    st.markdown('<span style="font-size:11.5px; font-weight:700; color:#64748b; letter-spacing:0.5px;">TRẠNG THÁI</span>', unsafe_allow_html=True)
with th_cols[4]:
    st.markdown('<span style="font-size:11.5px; font-weight:700; color:#64748b; letter-spacing:0.5px;">SỰ KIỆN</span>', unsafe_allow_html=True)
with th_cols[5]:
    st.markdown('<div style="text-align:right; font-size:11.5px; font-weight:700; color:#64748b; letter-spacing:0.5px;">THAO TÁC</div>', unsafe_allow_html=True)

st.markdown("<hr style='margin: 8px 0 12px 0; border: none; border-top: 1px solid #f1f5f9;'>", unsafe_allow_html=True)

if not sessions:
    notify.empty_state("Không tìm thấy phiên giám sát nào phù hợp", "Vui lòng thử tìm kiếm với từ khóa khác hoặc kiểm tra lại bộ lọc để hiển thị toàn bộ ca thi.")
else:
    for sess in sessions:
        sid = sess["PK_MaPhienGiamSat"]
        room = sess.get("PhongThi") or "Chưa đặt"
        subject = sess.get("MonThi") or "Chưa đặt"
        room_subject_label = f"{room} — {subject}"
        date_str = str(sess.get("ThoiGianBatDau", ""))[:16].replace("T", " ")
        ev_count = sess.get("so_su_kien", 0)
        status_badge = get_session_status_badge(sess.get("TrangThai"), sess.get("ThoiGianKetThuc"))

        row_cols = st.columns([1.2, 3.4, 1.8, 1.4, 0.8, 1.0])
        with row_cols[0]:
            st.markdown(f'<span style="font-size:13px; font-weight:600; color:#2563eb;">#SESS-{sid}</span>', unsafe_allow_html=True)
        with row_cols[1]:
            st.markdown(f'<span style="font-size:13.5px; font-weight:500; color:#0f172a;">{room_subject_label}</span>', unsafe_allow_html=True)
        with row_cols[2]:
            st.markdown(f'<span style="font-size:13px; color:#64748b;">{date_str}</span>', unsafe_allow_html=True)
        with row_cols[3]:
            st.markdown(status_badge, unsafe_allow_html=True)
        with row_cols[4]:
            st.markdown(f'<span style="font-size:13px; font-weight:600; color:#0f172a;">{ev_count}</span>', unsafe_allow_html=True)
        with row_cols[5]:
            action_html = (
                f'<div style="display:flex; align-items:center; justify-content:flex-end; gap:6px;">'
                f'  <a href="/session_detail?id={sid}" class="action-svg-btn view-btn" title="Xem chi tiết ca thi">'
                f'    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
                f'      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8z"/>'
                f'      <circle cx="12" cy="12" r="3"/>'
                f'    </svg>'
                f'  </a>'
                f'  <a href="/history?confirm_delete={sid}" class="action-svg-btn del-btn" title="Xóa phiên giám sát">'
                f'    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
                f'      <polyline points="3 6 5 6 21 6"/>'
                f'      <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>'
                f'      <line x1="10" y1="11" x2="10" y2="17"/>'
                f'      <line x1="14" y1="11" x2="14" y2="17"/>'
                f'    </svg>'
                f'  </a>'
                f'</div>'
            )
            st.markdown(action_html, unsafe_allow_html=True)

        st.markdown("<hr style='margin: 8px 0; border: none; border-top: 1px solid #f8fafc;'>", unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)

# ── Phân trang nhỏ gọn Figma Standard ─────────────────────
start_idx = (current_page - 1) * PAGE_SIZE + 1 if total_sessions_count > 0 else 0
end_idx = min(current_page * PAGE_SIZE, total_sessions_count)

st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)
pg_left, pg_spacer, pg_right = st.columns([5, 2, 5])

with pg_left:
    st.markdown(
        f"<div style='font-size: 13px; color: #64748b; line-height: 32px;'>"
        f"Hiển thị <strong>{start_idx} – {end_idx}</strong> trong tổng số <strong>{total_sessions_count}</strong> phiên"
        f"</div>",
        unsafe_allow_html=True,
    )

with pg_right:
    pag_items = []
    prev_disabled = "opacity: 0.35; pointer-events: none;" if current_page <= 1 else ""
    pag_items.append(f'<a href="/history?p={current_page - 1}" style="{prev_disabled}">‹</a>')

    for p in range(1, total_pages + 1):
        if total_pages > 7 and abs(p - current_page) > 2 and p != 1 and p != total_pages:
            if p == 2 or p == total_pages - 1:
                pag_items.append('<span style="color: #94a3b8; line-height: 32px; padding: 0 4px;">…</span>')
            continue
        active_cls = "active" if p == current_page else ""
        pag_items.append(f'<a href="/history?p={p}" class="{active_cls}">{p}</a>')

    next_disabled = "opacity: 0.35; pointer-events: none;" if current_page >= total_pages else ""
    pag_items.append(f'<a href="/history?p={current_page + 1}" style="{next_disabled}">›</a>')

    st.markdown(f'<div class="history-pagination">{"".join(pag_items)}</div>', unsafe_allow_html=True)

