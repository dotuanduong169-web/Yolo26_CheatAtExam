# -*- coding: utf-8 -*-
"""Trang sự kiện phiên: lưới sự kiện gian lận theo thời gian."""

import math

import streamlit as st
from streamlit_autorefresh import st_autorefresh

from components.app_sidebar import render_sidebar
from services.event_api import list_session_events
from services.history_api import get_all_sessions
from utils.auth_guard import require_auth
from utils.hide_streamlit_sidebar import hide_sidebar
from utils.http import init_session_state
from utils.load_css import load_css
from utils.render_header import render_page_header

# ── Config ──────────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="Sự kiện gian lận")

init_session_state()

if "events_page" not in st.session_state:
    st.session_state.events_page = 1
if "events_filter" not in st.session_state:
    st.session_state.events_filter = "Tất cả"

# ── Hidden buttons for page navigation ───────────────────────
col_a1, col_a2, col_a3, col_a4, col_a5 = st.columns(5)
with col_a1:
    st.markdown('<div id="hide-nav-row-analysis"></div>', unsafe_allow_html=True)
    if st.button("Go analysis 1", key="analysis_go_1", disabled=True):
        st.session_state.events_page = 1
with col_a2:
    if st.button("Go analysis 2", key="analysis_go_2", disabled=True):
        st.session_state.events_page = 2
with col_a3:
    if st.button("Go analysis 3", key="analysis_go_3", disabled=True):
        st.session_state.events_page = 3
with col_a4:
    if st.button("Go analysis 4", key="analysis_go_4", disabled=True):
        st.session_state.events_page = 4
with col_a5:
    if st.button("Go analysis 5", key="analysis_go_5", disabled=True):
        st.session_state.events_page = 5

st.markdown("""
<style>
    [data-testid="stHorizontalBlock"]:has(#hide-nav-row-analysis) {
        display: none !important;
    }
</style>
<script>
    (function() {
        const marker = document.getElementById('hide-nav-row-analysis');
        if (marker) {
            const row = marker.closest('[data-testid="stHorizontalBlock"]');
            if (row) {
                row.style.display = 'none';
                row.style.height = '0';
                row.style.margin = '0';
                row.style.padding = '0';
            }
        }
    })();
</script>
""", unsafe_allow_html=True)

require_auth()

# ── Sidebar & Styles ────────────────────────────────────────
hide_sidebar()
render_sidebar(active="events")
st.markdown(load_css("styles/sidebar.css"), unsafe_allow_html=True)
st.markdown(load_css("styles/session_analysis.css"), unsafe_allow_html=True)

# ── Session ID ──────────────────────────────────────────────
session_id = st.session_state.get("session_id") or st.session_state.get("selected_session")
if not session_id:
    st.warning("Chưa chọn phiên giám sát. Mở giám sát hoặc chọn trong Lịch sử.")
    st.stop()

# ── Session Name ────────────────────────────────────────────
room_name = f"#{session_id}"
all_sessions = get_all_sessions(st.session_state.client)
for s in all_sessions:
    if s.get("PK_MaPhienGiamSat") == session_id:
        room_name = s.get("PhongThi") or s.get("MonThi") or room_name
        break

# ── Header ──────────────────────────────────────────────────
render_page_header("Sự kiện gian lận")
if st.button("← Quay lại giám sát"):
    st.switch_page("pages/home.py")

st.markdown(f"""
<div class="header-meta">
    <span class="tag tag-blue">PHIÊN {session_id}</span>
    <span class="tag-text">Phòng: {room_name}</span>
</div>
""", unsafe_allow_html=True)

# ── Filter ──────────────────────────────────────────────────
flt = st.selectbox(
    "Lọc trạng thái",
    ["Tất cả", "cho_kiem_tra", "dung", "sai"],
    index=["Tất cả", "cho_kiem_tra", "dung", "sai"].index(st.session_state.events_filter),
)
if flt != st.session_state.events_filter:
    st.session_state.events_filter = flt
    st.session_state.events_page = 1
    st.rerun()

trang_thai = "" if flt == "Tất cả" else flt
events = list_session_events(st.session_state.client, session_id, trang_thai=trang_thai, limit=200)

st.markdown(
    '<div class="section-title">Dòng thời gian sự kiện (mới nhất trước)</div>',
    unsafe_allow_html=True,
)

if not events:
    st.info("Chưa có sự kiện nào.")
    st.stop()

# ── Pagination ──────────────────────────────────────────────
PER_PAGE = 6
total = len(events)
pages = max(1, math.ceil(total / PER_PAGE))
page = min(st.session_state.events_page, pages)
st.session_state.events_page = page

start = (page - 1) * PER_PAGE
show_events = events[start:start + PER_PAGE]

row1 = show_events[:3]
row2 = show_events[3:6]


def render_card(item, col):
    """Vẽ một thẻ sự kiện."""
    with col:
        pending = item.get("TrangThaiKiemTra") == "cho_kiem_tra"
        card_cls = "frame-card alert" if pending else "frame-card"
        status_cls = "warning" if pending else "active"
        status_text = "CHỜ KIỂM TRA" if pending else item.get("TrangThaiKiemTra", "").upper()

        raw_time = str(item.get("ThoiGianPhatHien", ""))
        time_short = raw_time.split("T")[-1][:8] if "T" in raw_time else raw_time[:8]
        label = item.get("LoaiHanhVi", "?")
        conf = round(float(item.get("DoTinCay", 0)) * 100, 1)

        st.markdown(f'<div class="{card_cls}">', unsafe_allow_html=True)
        st.markdown(f"""
        <div class="img-container">
            <div class="time-overlay">{time_short}</div>
            <div class="status-overlay {status_cls}">{status_text}</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="card-info-title">{label} · {conf}%</div>
        <div class="card-info-time">Phát hiện lúc {raw_time[:19]}</div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="stats-row">
            <div class="stat-box">
                <div class="stat-label">NHÃN AI</div>
                <div class="stat-value blue">{item.get("NhanAI", "?")}</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">NHÃN SỬA</div>
                <div class="stat-value red">{item.get("NhanNguoiDung") or "—"}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("Xem chi tiết", use_container_width=True, key=f"evdetail_{item['PK_MaSuKien']}"):
            st.session_state["event_id"] = item["PK_MaSuKien"]
            st.switch_page("pages/event_detail.py")

        st.markdown("</div>", unsafe_allow_html=True)


if row1:
    cols1 = st.columns(3)
    for i, item in enumerate(row1):
        render_card(item, cols1[i])

if row2:
    cols2 = st.columns(3)
    for i, item in enumerate(row2):
        render_card(item, cols2[i])

# ── Pagination row ──────────────────────────────────────────
st.markdown('<div id="analysis-pagination-row">', unsafe_allow_html=True)
info_col, prev_col, nums_col, next_col = st.columns([4, 1, 4, 1], gap="small")

with info_col:
    st.markdown(
        f"<div class='pg-info-label'>Hiển thị {len(show_events)} trong số {total} sự kiện</div>",
        unsafe_allow_html=True,
    )

p_start = max(1, page - 2)
p_end = min(pages, page + 2)
page_btns_html = ""
if p_start > 1:
    page_btns_html += '<span class="pg-btn">1</span><span class="pg-btn disabled">…</span>'
for p in range(p_start, p_end + 1):
    active = "active" if p == page else ""
    page_btns_html += f'<span class="pg-btn {active}" data-page="{p}">{p}</span>'
if p_end < pages:
    page_btns_html += f'<span class="pg-btn disabled">…</span><span class="pg-btn">{pages}</span>'

with nums_col:
    st.markdown(
        f"<div class='pg-nums-bar'>{page_btns_html}</div>",
        unsafe_allow_html=True,
    )

with prev_col:
    if st.button("‹", disabled=(page <= 1), key="pg_prev"):
        st.session_state.events_page -= 1
        st.rerun()

with next_col:
    if st.button("›", disabled=(page >= pages), key="pg_next"):
        st.session_state.events_page += 1
        st.rerun()

st.markdown('</div>', unsafe_allow_html=True)

st.markdown("""
<script>
    document.querySelectorAll('#analysis-pagination-row .pg-btn[data-page]').forEach(btn => {
        btn.style.cursor = 'pointer';
        btn.addEventListener('click', function() {
            const page = parseInt(this.dataset.page);
            const hiddenBtn = document.querySelector('button[data-testid*="analysis_go_' + page + '"]');
            if (hiddenBtn) hiddenBtn.click();
        });
    });
</script>
""", unsafe_allow_html=True)

# ── Auto Refresh ────────────────────────────────────────────
if st.session_state.get("running", False):
    st_autorefresh(interval=10000, key="events_refresh")
