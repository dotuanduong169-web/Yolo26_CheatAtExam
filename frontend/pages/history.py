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
    notify.warning("Bạn có chắc chắn muốn xóa phiên giám sát này không?")
    st.caption("Hành động này sẽ xóa vĩnh viễn toàn bộ sự kiện và hình ảnh bằng chứng liên quan.")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Hủy bỏ", use_container_width=True):
            st.rerun()
    with c2:
        if st.button("Xác nhận xóa", type="primary", use_container_width=True):
            handle_delete(session_id)


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
st.markdown('<div class="table-card">', unsafe_allow_html=True)

st.markdown("""
<div class="table-header-row">
    <span>MÃ PHIÊN</span>
    <span>PHÒNG / MÔN THI</span>
    <span>THỜI GIAN BẮT ĐẦU</span>
    <span>TRẠNG THÁI</span>
    <span>SỰ KIỆN</span>
    <span style="text-align:right">THAO TÁC</span>
</div>
""", unsafe_allow_html=True)

if not sessions:
    st.markdown("""
    <div style="padding:40px 24px; text-align:center; color:#9ca3af;">
        <div style="font-size:14px; font-weight:500;">Không tìm thấy phiên giám sát nào phù hợp.</div>
    </div>
    """, unsafe_allow_html=True)
else:
    for sess in sessions:
        sid = sess["PK_MaPhienGiamSat"]
        room = sess.get("PhongThi") or "Chưa đặt"
        subject = sess.get("MonThi") or "Chưa đặt"
        room_subject_label = f"{room} — {subject}"
        date_str = str(sess.get("ThoiGianBatDau", ""))[:16].replace("T", " ")
        ev_count = sess.get("so_su_kien", 0)
        status_badge = get_session_status_badge(sess.get("TrangThai"), sess.get("ThoiGianKetThuc"))

        row_cols = st.columns([1.1, 2.0, 1.4, 1.2, 0.8, 1.0])
        with row_cols[0]:
            st.markdown(f'<span class="cell-session-id">#SESS-{sid}</span>', unsafe_allow_html=True)
        with row_cols[1]:
            st.markdown(f'<span class="cell-class">{room_subject_label}</span>', unsafe_allow_html=True)
        with row_cols[2]:
            st.markdown(f'<span class="cell-date">{date_str}</span>', unsafe_allow_html=True)
        with row_cols[3]:
            st.markdown(status_badge, unsafe_allow_html=True)
        with row_cols[4]:
            st.markdown(f'<span class="cell-count">{ev_count}</span>', unsafe_allow_html=True)
        with row_cols[5]:
            h_col1, h_col2 = st.columns([1, 1])
            with h_col1:
                st.markdown('<div class="btn-icon-action btn-icon-view">', unsafe_allow_html=True)
                if st.button("Xem", key=f"view_{sid}", help="Xem chi tiết phiên giám sát", use_container_width=True):
                    st.session_state.selected_session = sid
                    st.switch_page("pages/session_detail.py")
                st.markdown('</div>', unsafe_allow_html=True)
            with h_col2:
                st.markdown('<div class="btn-icon-action btn-icon-delete">', unsafe_allow_html=True)
                if st.button("Xóa", key=f"del_{sid}", help="Xóa phiên giám sát", use_container_width=True):
                    confirm_delete(sid)
                st.markdown('</div>', unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)

# ── Pagination (Native Streamlit Buttons - Không dùng JS hack) ──
start_idx = (current_page - 1) * PAGE_SIZE + 1 if total_sessions_count > 0 else 0
end_idx = min(current_page * PAGE_SIZE, total_sessions_count)

st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)
pg_left, pg_right = st.columns([4, 6])

with pg_left:
    st.markdown(
        f"<div style='font-size: 13px; color: var(--wf-text-muted); padding-top: 6px;'>"
        f"Hiển thị {start_idx} – {end_idx} trong tổng số {total_sessions_count} phiên"
        f"</div>",
        unsafe_allow_html=True,
    )

with pg_right:
    # Xây dựng các trang hiển thị
    pages_to_show = []
    if total_pages <= 7:
        pages_to_show = list(range(1, total_pages + 1))
    else:
        if current_page <= 4:
            pages_to_show = [1, 2, 3, 4, 5, "...", total_pages]
        elif current_page >= total_pages - 3:
            pages_to_show = [1, "..."] + list(range(total_pages - 4, total_pages + 1))
        else:
            pages_to_show = [1, "...", current_page - 1, current_page, current_page + 1, "...", total_pages]

    num_btn_cols = len(pages_to_show) + 2
    btn_cols = st.columns(num_btn_cols)

    # Nút Previous (‹)
    with btn_cols[0]:
        if st.button("‹", key="btn_prev_page", disabled=(current_page <= 1), use_container_width=True):
            st.session_state.hist_page -= 1
            st.rerun()

    # Các nút số trang
    for idx, p in enumerate(pages_to_show):
        with btn_cols[idx + 1]:
            if p == "...":
                st.markdown("<div style='text-align: center; line-height: 38px; color: #94a3b8;'>…</div>", unsafe_allow_html=True)
            else:
                is_active = (p == current_page)
                btn_type = "primary" if is_active else "secondary"
                if st.button(str(p), key=f"page_num_{p}", type=btn_type, use_container_width=True):
                    if p != current_page:
                        st.session_state.hist_page = p
                        st.rerun()

    # Nút Next (›)
    with btn_cols[-1]:
        if st.button("›", key="btn_next_page", disabled=(current_page >= total_pages), use_container_width=True):
            st.session_state.hist_page += 1
            st.rerun()

