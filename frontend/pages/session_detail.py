# -*- coding: utf-8 -*-
"""Trang chi tiết phiên lịch sử: thẻ KPI, biểu đồ tròn và bảng khung hình.
Luồng chính: tải chi tiết phiên -> tính phần trăm tập trung -> vẽ biểu đồ và bảng phân trang."""

import math

import streamlit as st
import plotly.graph_objects as go

from components.app_sidebar import render_sidebar
from services.history_api import get_session_detail
from utils.auth_guard import require_auth
from utils.hide_streamlit_sidebar import hide_sidebar
from utils.http import init_session_state
from utils.load_css import load_css
from utils.render_header import render_page_header

# ── Cấu hình trang ────────────────────────────────────────
st.set_page_config(layout="wide", page_title="Chi tiết phiên")

init_session_state()
require_auth()

if "detail_page" not in st.session_state:
    st.session_state.detail_page = 1

# ── Nút ẩn để chuyển trang chi tiết ───────────────────────
col_h1, col_h2, col_h3, col_h4, col_h5 = st.columns(5)
with col_h1:
    st.markdown('<div id="hide-nav-row-detail"></div>', unsafe_allow_html=True)
    if st.button("Go detail 1", key="detail_go_1", disabled=True):
        st.session_state.detail_page = 1
with col_h2:
    if st.button("Go detail 2", key="detail_go_2", disabled=True):
        st.session_state.detail_page = 2
with col_h3:
    if st.button("Go detail 3", key="detail_go_3", disabled=True):
        st.session_state.detail_page = 3
with col_h4:
    if st.button("Go detail 4", key="detail_go_4", disabled=True):
        st.session_state.detail_page = 4
with col_h5:
    if st.button("Go detail 5", key="detail_go_5", disabled=True):
        st.session_state.detail_page = 5

st.markdown("""
<style>
    /* Dự phòng bằng CSS */
    [data-testid="stHorizontalBlock"]:has(#hide-nav-row-detail) {
        display: none !important;
    }
</style>
<script>
    (function() {
        const marker = document.getElementById('hide-nav-row-detail');
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

# ── Thanh bên và CSS ──────────────────────────────────────
hide_sidebar()
st.markdown(load_css("styles/sidebar.css"), unsafe_allow_html=True)
render_sidebar(active="history")
st.markdown(load_css("styles/session_detail.css"), unsafe_allow_html=True)

# ── Lấy mã phiên đã chọn ──────────────────────────────────
session_id = st.session_state.get("selected_session")
if not session_id:
    st.error("Thiếu session_id")
    st.stop()


# ── Tải dữ liệu phiên ───────────────────────────────────────
data = get_session_detail(st.session_state.client, session_id)
if not data:
    st.error("Không lấy được dữ liệu")
    st.stop()

frames = data.get("frames", [])
total_students = data.get("total_students", 0)
sleeping = data.get("sleeping", 0)
alerts = data.get("alerts", 0)
duration = data.get("duration", 0)
focus_rate = data.get("focus_rate", 0)
class_id = data.get("class_id", "N/A")

# Tính phần trăm cho biểu đồ tròn
focus_pct = round(focus_rate * 100)
sleeping_pct = 100 - focus_pct

# ── Tiêu đề trang ─────────────────────────────────────────
render_page_header("Chi tiết lịch sử phiên")

# ── Nút quay lại và trạng thái phiên ──────────────────────

st.markdown("""
<a href="/history" target="_self" class="back-btn" style="text-decoration: none;">
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M19 12H5M12 19l-7-7 7-7"/>
    </svg>
    Chi tiết lịch sử phiên
</a>
""", unsafe_allow_html=True)

status_text = "ĐANG CHẠY" if data.get("is_active") else "HOÀN THÀNH"
status_cls = "status-running" if data.get("is_active") else "status-done"

st.markdown(f"""
<div class="page-header">
    <div class="title">Chi tiết phiên #SESS-{session_id}</div>
    <div class="status-badge {status_cls}">{status_text}</div>
</div>
""", unsafe_allow_html=True)

# ── Hàng trên: biểu đồ + 2 cột KPI ────────────────────────
top1, top2, top3 = st.columns([1, 1, 1], gap="medium")

# -- Cột biểu đồ hành vi --
with top1:
    st.markdown('<div class="card-title">🎯 Phân bổ hành vi</div>', unsafe_allow_html=True)

    labels = ["Tập trung", "Xao nhãng", "Buồn ngủ"]
    vals = [focus_pct, 0, sleeping_pct]
    colors = ["#1677ff", "#ff9f43", "#ef4444"]

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=vals,
        hole=0.75,
        marker=dict(colors=colors),
        textinfo="none",
        hoverinfo="label+percent",
        sort=False,
        direction="clockwise",
    )])
    fig.update_layout(
        height=180,
        margin=dict(l=0, r=0, t=0, b=0),
        showlegend=False,
        annotations=[dict(
            text=f"Tập trung<br><b style='font-size:24px; color:#1e293b;'>{int(focus_pct)}%</b>",
            showarrow=False,
            font=dict(size=12, color="#64748b"),
        )],
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )

    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # Chú giải dưới biểu đồ (đóng thẻ card biểu đồ)
    st.markdown(f"""
        <div class="legend-list">
            <div class="legend-item">
                <div class="legend-label">
                    <span class="legend-dot blue"></span>
                    <span>Tập trung</span>
                </div>
                <span class="legend-val">{int(focus_pct)}%</span>
            </div>
            <div class="legend-item">
                <div class="legend-label">
                    <span class="legend-dot amber"></span>
                    <span>Xao nhãng</span>
                </div>
                <span class="legend-val">0%</span>
            </div>
            <div class="legend-item">
                <div class="legend-label">
                    <span class="legend-dot red"></span>
                    <span>Buồn ngủ</span>
                </div>
                <span class="legend-val">{int(sleeping_pct)}%</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

# -- Cột KPI thứ hai --
with top2:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Tổng số sinh viên</div>
        <div>
            <span class="kpi-value">{total_students}</span>
            <span class="kpi-unit">người</span>
        </div>
        <div class="kpi-sub green">↗ Đầy đủ 100%</div>
    </div>
    """, unsafe_allow_html=True)

    warn_sub = "⚠ Cần lưu ý" if alerts > 0 else "✓ Tốt"
    warn_cls = "warn" if alerts > 0 else "green"
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Tổng số cảnh báo</div>
        <div>
            <span class="kpi-value orange">{alerts:02d}</span>
            <span class="kpi-unit">lần</span>
        </div>
        <div class="kpi-sub {warn_cls}">{warn_sub}</div>
    </div>
    """, unsafe_allow_html=True)

# -- Cột KPI thứ ba --
with top3:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Độ chính xác trung bình</div>
        <div>
            <span class="kpi-value blue">{focus_pct}</span>
            <span class="kpi-unit">%</span>
        </div>
        <div class="kpi-sub">Tính dựa trên dữ liệu AI Recognition</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Thời gian học thực tế</div>
        <div>
            <span class="kpi-value">{int(duration)}</span>
            <span class="kpi-unit">phút</span>
        </div>
        <div class="kpi-sub green">Bắt đầu đúng giờ</div>
    </div>
    """, unsafe_allow_html=True)

# ── Bảng khung hình ───────────────────────────────────────
PAGE_SIZE = 5
total_rows = len(frames)
total_pages = max(1, math.ceil(total_rows / PAGE_SIZE))

# Giữ số trang trong giới hạn hợp lệ
st.session_state.detail_page = min(st.session_state.detail_page, total_pages)
page = st.session_state.detail_page

start = (page - 1) * PAGE_SIZE
end = start + PAGE_SIZE
page_frames = frames[start:end]

# -- Khối chứa bảng --
table_container = st.container()
with table_container:
    st.markdown(f"""
        <div class="table-header">
            <span class="table-title">Danh sách khung hình (Interval 30s)</span>
            <div class="filter-icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"></polygon>
                </svg>
            </div>
        </div>
    """, unsafe_allow_html=True)

    if not frames:
        st.info("Chưa có dữ liệu frame")
    else:
        # Tiêu đề cột của bảng
        st.markdown("""
            <div class="tbl-head-row">
                <div style="flex: 1.2;" class="tbl-head">MỐC THỜI GIAN</div>
                <div style="flex: 1.2;" class="tbl-head">TRẠNG THÁI</div>
                <div style="flex: 1;" class="tbl-head">SỐ LƯỢNG SINH VIÊN</div>
                <div style="flex: 1.5;" class="tbl-head">ĐỘ CHÍNH XÁC</div>
                <div style="flex: 1;" class="tbl-head">CA BUỒN NGỦ</div>
                <div style="flex: 1;" class="tbl-head">THAO TÁC</div>
            </div>
        """, unsafe_allow_html=True)

    # Các hàng của bảng
    for row in page_frames:
        c1, c2, c3, c4, c5, c6 = st.columns([1.2, 1.2, 1, 1.5, 1, 1])

        # Mốc thời gian (in đậm)
        c1.markdown(
            f"<div class='tbl-cell'><b>{row['time']}</b></div>",
            unsafe_allow_html=True,
        )

        # Huy hiệu trạng thái
        is_alert = row["status"] != "Normal"
        badge_cls = "badge-warning" if is_alert else "badge-normal"
        badge_text = "CẢNH BÁO" if is_alert else "BÌNH THƯỜNG"
        c2.markdown(
            f"<div class='tbl-cell'><span class='badge {badge_cls}'>{badge_text}</span></div>",
            unsafe_allow_html=True,
        )

        # Số lượng sinh viên
        c3.markdown(
            f"<div class='tbl-cell'>{row['students']} SV</div>",
            unsafe_allow_html=True,
        )

        # Độ chính xác (in đậm + gạch chân)
        acc = row["accuracy"]
        c4.markdown(f"""
        <div class='tbl-cell'>
            <span style="font-weight:700; border-bottom: 2px solid #1677ff; padding-bottom: 2px;">{acc}%</span>
        </div>
        """, unsafe_allow_html=True)

        # Số ca buồn ngủ (đỏ + in đậm)
        sl = row["sleeping"]
        if sl > 0:
            c5.markdown(
                f"<div class='tbl-cell'><span class='sleep-count' style='color:#ef4444; font-weight:700;'>{sl:02d} ca</span></div>",
                unsafe_allow_html=True,
            )
        else:
            c5.markdown(
                "<div class='tbl-cell'><span class='sleep-none'>--</span></div>",
                unsafe_allow_html=True,
            )

        # Thao tác (kiểu liên kết xanh)
        with c6:
            if st.button("Xem chi tiết", key=f"view_{row['frame_id']}", use_container_width=True, type="secondary"):
                st.session_state["frame_id"] = row["frame_id"]
                st.switch_page("pages/frame_detail.py")

    # ── Phân trang ──────────────────────────────────────────
    showing = len(page_frames)

    # ── Hàng phân trang thống nhất ──────────────────────────
    st.markdown('<div id="detail-pagination-row">', unsafe_allow_html=True)
    info_col, prev_col, nums_col, next_col = st.columns([4, 1, 4, 1], gap="small")

    with info_col:
        st.markdown(
            f"<div class='pg-info-text'>Hiển thị {showing} trên {total_rows} khung hình</div>",
            unsafe_allow_html=True,
        )

    # Dựng HTML số trang
    p_start = max(1, page - 2)
    p_end = min(total_pages, page + 2)
    page_btns_html = ""
    if p_start > 1:
        page_btns_html += '<span class="page-btn">1</span><span class="page-btn disabled">…</span>'
    for p in range(p_start, p_end + 1):
        active = "active" if p == page else ""
        page_btns_html += f'<span class="page-btn {active}" data-page="{p}">{p}</span>'
    if p_end < total_pages:
        page_btns_html += f'<span class="page-btn disabled">…</span><span class="page-btn">{total_pages}</span>'

    with nums_col:
        st.markdown(
            f"<div class='pg-buttons-container'>{page_btns_html}</div>",
            unsafe_allow_html=True,
        )

    with prev_col:
        if st.button("‹", disabled=(page <= 1), key="page_prev"):
            st.session_state.detail_page -= 1
            st.rerun()

    with next_col:
        if st.button("›", disabled=(page >= total_pages), key="page_next"):
            st.session_state.detail_page += 1
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

    # ── JS bắt click vào số trang ───────────────────────────
    st.markdown(f"""
    <script>
        document.querySelectorAll('#detail-pagination-row .page-btn[data-page]').forEach(btn => {{
            btn.style.cursor = 'pointer';
            btn.addEventListener('click', function() {{
                const page = parseInt(this.dataset.page);
                const hiddenBtn = document.querySelector('button[data-testid*="detail_go_' + page + '"]');
                if (hiddenBtn) hiddenBtn.click();
            }});
        }});
    </script>
    """, unsafe_allow_html=True)