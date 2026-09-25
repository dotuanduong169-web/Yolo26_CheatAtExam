# -*- coding: utf-8 -*-
"""Trang kết quả phân tích của phiên đang chạy: lưới khung hình theo thời gian.
Luồng chính: lấy tên lớp -> lấy phân tích frame -> chia trang 6 khung hình -> vẽ thẻ."""

import math

import streamlit as st
from streamlit_autorefresh import st_autorefresh

from components.app_sidebar import render_sidebar
from services.frame_api import get_frame_analysis
from services.history_api import get_all_sessions
from utils.auth_guard import require_auth
from utils.hide_streamlit_sidebar import hide_sidebar
from utils.http import init_session_state
from utils.load_css import load_css
from utils.render_header import render_page_header

# ── Cấu hình trang ────────────────────────────────────────
st.set_page_config(layout="wide", page_title="Kết quả phân tích")

init_session_state()

if "analysis_page" not in st.session_state:
    st.session_state.analysis_page = 1

# ── Nút ẩn để chuyển trang phân tích ──────────────────────
col_a1, col_a2, col_a3, col_a4, col_a5 = st.columns(5)
with col_a1:
    st.markdown('<div id="hide-nav-row-analysis"></div>', unsafe_allow_html=True)
    if st.button("Go analysis 1", key="analysis_go_1", disabled=True):
        st.session_state.analysis_page = 1
with col_a2:
    if st.button("Go analysis 2", key="analysis_go_2", disabled=True):
        st.session_state.analysis_page = 2
with col_a3:
    if st.button("Go analysis 3", key="analysis_go_3", disabled=True):
        st.session_state.analysis_page = 3
with col_a4:
    if st.button("Go analysis 4", key="analysis_go_4", disabled=True):
        st.session_state.analysis_page = 4
with col_a5:
    if st.button("Go analysis 5", key="analysis_go_5", disabled=True):
        st.session_state.analysis_page = 5

st.markdown("""
<style>
    /* Dự phòng bằng CSS */
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

# ── Thanh bên và CSS ──────────────────────────────────────
hide_sidebar()
render_sidebar(active="home")
st.markdown(load_css("styles/sidebar.css"), unsafe_allow_html=True)
st.markdown(load_css("styles/session_analysis.css"), unsafe_allow_html=True)

# ── Lấy mã phiên đang chạy ────────────────────────────────
session_id = st.session_state.get("session_id")
if not session_id:
    st.warning("Không có phiên học đang chạy.")
    st.stop()

# ── Tra tên lớp theo mã phiên ─────────────────────────────
class_name = "UNKNOWN"
all_sessions = get_all_sessions(st.session_state.client)
for s in all_sessions:
    if s["session_id"] == session_id:
        class_name = s["class_id"]
        break

# ── Tải dữ liệu phân tích khung hình ───────────────────────
frames = get_frame_analysis(st.session_state.client, session_id)

# ── Tiêu đề trang ─────────────────────────────────────────
render_page_header("Kết quả phân tích")
if st.button("← Quay lại giám sát"):
    st.switch_page("pages/home.py")

st.markdown(f"""
<div class="header-meta">
    <span class="tag tag-blue">PHÒNG {session_id}</span>
    <span class="tag-text">Phiên học: {class_name}</span>
</div>
""", unsafe_allow_html=True)

st.markdown(
    '<div class="section-title">Dòng thời gian trích xuất (Mỗi 30 giây)</div>',
    unsafe_allow_html=True,
)

if not frames:
    st.info("Chưa có dữ liệu phân tích.")
    st.stop()

# ── Chia trang 6 khung hình mỗi trang ──────────────────────
PER_PAGE = 6
total = len(frames)
pages = max(1, math.ceil(total / PER_PAGE))
page = min(st.session_state.analysis_page, pages)
st.session_state.analysis_page = page

start = (page - 1) * PER_PAGE
show_frames = frames[start:start + PER_PAGE]

# ── Lưới 3 cột, 2 hàng ────────────────────────────────────
# Cắt thành từng hàng 3 thẻ
row1 = show_frames[:3]
row2 = show_frames[3:6]


def render_card(item, col):
    """Vẽ một thẻ khung hình bên trong cột Streamlit."""
    with col:
        is_alert = item["sleeping_count"] > 0
        card_cls = "frame-card alert" if is_alert else "frame-card"
        status_cls = "warning" if is_alert else "active"
        status_text = "CẢNH BÁO" if is_alert else "ĐANG HOẠT ĐỘNG"

        # Định dạng giờ để phủ lên ảnh
        raw_time = str(item.get("extracted_at", ""))
        # Cắt lấy phần giờ:phút:giây
        time_short = raw_time.split("T")[-1][:8] if "T" in raw_time else raw_time[:8]

        # Mở thẻ card
        st.markdown(f'<div class="{card_cls}">', unsafe_allow_html=True)

        # Ảnh kèm lớp phủ trạng thái
        st.markdown(f"""
        <div class="img-container">
            <div class="time-overlay">{time_short}</div>
            <div class="status-overlay {status_cls}">{status_text}</div>
        </div>
        """, unsafe_allow_html=True)

        st.image(item["image_path"], use_container_width=True)

        # Thông tin thẻ
        st.markdown(f"""
        <div class="card-info-title">Phân tích khung hình #{item["frame_id"]}</div>
        <div class="card-info-time">Trích xuất lúc {raw_time}</div>
        """, unsafe_allow_html=True)

        # Hàng số liệu tập trung/buồn ngủ
        sleep_cls = "stat-box alert-box" if is_alert else "stat-box"
        st.markdown(f"""
        <div class="stats-row">
            <div class="stat-box">
                <div class="stat-label">TẬP TRUNG</div>
                <div class="stat-value blue">{item["focus_count"]:02d}</div>
            </div>
            <div class="{sleep_cls}">
                <div class="stat-label">BUỒN NGỦ</div>
                <div class="stat-value red">{item["sleeping_count"]:02d}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Nút xem chi tiết khung hình
        if st.button("Xem chi tiết", use_container_width=True, key=f"detail_{item['frame_id']}"):
            st.session_state["frame_id"] = item["frame_id"]
            st.switch_page("pages/frame_detail.py")

        # Đóng thẻ card
        st.markdown("</div>", unsafe_allow_html=True)


# Vẽ hàng 1
if row1:
    cols1 = st.columns(3)
    for i, item in enumerate(row1):
        render_card(item, cols1[i])

# Vẽ hàng 2
if row2:
    cols2 = st.columns(3)
    for i, item in enumerate(row2):
        render_card(item, cols2[i])

# ── Đếm số khung hình đang hiện ─────────────────────────────
showing = len(show_frames)


# ── Hàng phân trang ─────────────────────────────────────────
st.markdown('<div id="analysis-pagination-row">', unsafe_allow_html=True)
info_col, prev_col, nums_col, next_col = st.columns([4, 1, 4, 1], gap="small")

with info_col:
    st.markdown(
        f"<div class='pg-info-label'>Hiển thị {showing} trong số {total} khung hình</div>",
        unsafe_allow_html=True,
    )

# Dựng HTML số trang
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
        st.session_state.analysis_page -= 1
        st.rerun()

with next_col:
    if st.button("›", disabled=(page >= pages), key="pg_next"):
        st.session_state.analysis_page += 1
        st.rerun()

st.markdown('</div>', unsafe_allow_html=True)

# ── JS bắt click vào số trang ─────────────────────────────
st.markdown(f"""
<script>
    document.querySelectorAll('#analysis-pagination-row .pg-btn[data-page]').forEach(btn => {{
        btn.style.cursor = 'pointer';
        btn.addEventListener('click', function() {{
            const page = parseInt(this.dataset.page);
            const hiddenBtn = document.querySelector('button[data-testid*="analysis_go_' + page + '"]');
            if (hiddenBtn) hiddenBtn.click();
        }});
    }});
</script>
""", unsafe_allow_html=True)



# ── Tự làm mới khi phiên đang chạy ────────────────────────
if st.session_state.get("running", False):
    st_autorefresh(interval=10000, key="analysis_refresh")