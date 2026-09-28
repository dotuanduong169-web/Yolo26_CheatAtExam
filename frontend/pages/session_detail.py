# -*- coding: utf-8 -*-
"""Trang chi tiết phiên: KPI, biểu đồ tròn và bảng sự kiện."""

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

# ── Config ──────────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="Chi tiết phiên")

init_session_state()
require_auth()

if "detail_page" not in st.session_state:
    st.session_state.detail_page = 1

# ── Hidden buttons for page navigation ───────────────────────
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

# ── Sidebar & Styles ────────────────────────────────────────
hide_sidebar()
st.markdown(load_css("styles/sidebar.css"), unsafe_allow_html=True)
render_sidebar(active="history")
st.markdown(load_css("styles/session_detail.css"), unsafe_allow_html=True)

# ── Session ID ──────────────────────────────────────────────
session_id = st.session_state.get("selected_session")
if not session_id:
    st.error("Thiếu session_id")
    st.stop()


# ── Load Data ───────────────────────────────────────────────
data = get_session_detail(st.session_state.client, session_id)
if not data:
    st.error("Không lấy được dữ liệu")
    st.stop()

sess = data.get("session", {})
events = data.get("events", [])
tong = data.get("tong_su_kien", len(events))
cho_kt = data.get("cho_kiem_tra", 0)
da_xm = data.get("da_xac_minh", tong - cho_kt)
ty_le_sach = data.get("ty_le_sach", 1.0)
room = sess.get("PhongThi") or sess.get("MonThi") or f"#{session_id}"
is_active = (sess.get("TrangThai") == "dang_giam_sat")

clean_pct = round(ty_le_sach * 100)
cheat_pct = 100 - clean_pct

# ── Page Header ─────────────────────────────────────────────
render_page_header("Chi tiết lịch sử phiên")

st.markdown("""
<a href="/history" target="_self" class="back-btn" style="text-decoration: none;">
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M19 12H5M12 19l-7-7 7-7"/>
    </svg>
    Chi tiết lịch sử phiên
</a>
""", unsafe_allow_html=True)

status_text = "ĐANG CHẠY" if is_active else "HOÀN THÀNH"
status_cls = "status-running" if is_active else "status-done"

st.markdown(f"""
<div class="page-header">
    <div class="title">Chi tiết phiên {room} (#{session_id})</div>
    <div class="status-badge {status_cls}">{status_text}</div>
</div>
""", unsafe_allow_html=True)

# ── Top Row: Chart + KPI ────────────────────────────────────
top1, top2, top3 = st.columns([1, 1, 1], gap="medium")

with top1:
    st.markdown('<div class="card-title">🎯 Tỉ lệ sạch / gian lận</div>', unsafe_allow_html=True)

    labels = ["Sạch", "Gian lận"]
    vals = [clean_pct, cheat_pct]
    colors = ["#1677ff", "#ef4444"]

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
            text=f"Sạch<br><b style='font-size:24px; color:#1e293b;'>{int(clean_pct)}%</b>",
            showarrow=False,
            font=dict(size=12, color="#64748b"),
        )],
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )

    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    st.markdown(f"""
        <div class="legend-list">
            <div class="legend-item">
                <div class="legend-label">
                    <span class="legend-dot blue"></span>
                    <span>Sạch</span>
                </div>
                <span class="legend-val">{int(clean_pct)}%</span>
            </div>
            <div class="legend-item">
                <div class="legend-label">
                    <span class="legend-dot red"></span>
                    <span>Gian lận</span>
                </div>
                <span class="legend-val">{int(cheat_pct)}%</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

with top2:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Tổng sự kiện gian lận</div>
        <div>
            <span class="kpi-value orange">{tong:02d}</span>
            <span class="kpi-unit">sự kiện</span>
        </div>
        <div class="kpi-sub {'warn' if tong > 0 else 'green'}">{'⚠ Cần lưu ý' if tong > 0 else '✓ Tốt'}</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Chờ kiểm tra</div>
        <div>
            <span class="kpi-value">{cho_kt:02d}</span>
            <span class="kpi-unit">sự kiện</span>
        </div>
        <div class="kpi-sub">Đã xác minh {da_xm}</div>
    </div>
    """, unsafe_allow_html=True)

with top3:
    start = str(sess.get("ThoiGianBatDau", ""))[:16]
    end = str(sess.get("ThoiGianKetThuc", "") or "—")[:16]
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Bắt đầu</div>
        <div>
            <span class="kpi-value blue" style="font-size:20px">{start}</span>
        </div>
        <div class="kpi-sub">Kết thúc: {end}</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Phòng / Môn</div>
        <div>
            <span class="kpi-value" style="font-size:20px">{sess.get("PhongThi") or "—"}</span>
        </div>
        <div class="kpi-sub green">{sess.get("MonThi") or ""}</div>
    </div>
    """, unsafe_allow_html=True)

# ── Events Table ────────────────────────────────────────────
PAGE_SIZE = 5
total_rows = len(events)
total_pages = max(1, math.ceil(total_rows / PAGE_SIZE))

st.session_state.detail_page = min(st.session_state.detail_page, total_pages)
page = st.session_state.detail_page

start = (page - 1) * PAGE_SIZE
end = start + PAGE_SIZE
page_events = events[start:end]

table_container = st.container()
with table_container:
    st.markdown("""
        <div class="table-header">
            <span class="table-title">Danh sách sự kiện gian lận</span>
        </div>
    """, unsafe_allow_html=True)

    if not events:
        st.info("Chưa có sự kiện nào")
    else:
        st.markdown("""
            <div class="tbl-head-row">
                <div style="flex: 1.2;" class="tbl-head">THỜI GIAN</div>
                <div style="flex: 1.2;" class="tbl-head">HÀNH VI</div>
                <div style="flex: 1;" class="tbl-head">ĐỘ TIN CẬY</div>
                <div style="flex: 1.5;" class="tbl-head">TRẠNG THÁI</div>
                <div style="flex: 1;" class="tbl-head">THAO TÁC</div>
            </div>
        """, unsafe_allow_html=True)

    for row in page_events:
        c1, c2, c3, c4, c5 = st.columns([1.2, 1.2, 1, 1.5, 1])

        c1.markdown(
            f"<div class='tbl-cell'><b>{str(row.get('ThoiGianPhatHien', ''))[:19]}</b></div>",
            unsafe_allow_html=True,
        )

        c2.markdown(
            f"<div class='tbl-cell'>{row.get('LoaiHanhVi', '?')}</div>",
            unsafe_allow_html=True,
        )

        c3.markdown(
            f"<div class='tbl-cell'>{round(float(row.get('DoTinCay', 0)) * 100, 1)}%</div>",
            unsafe_allow_html=True,
        )

        stt = row.get("TrangThaiKiemTra", "cho_kiem_tra")
        badge_cls = "badge-warning" if stt == "cho_kiem_tra" else "badge-normal"
        c4.markdown(
            f"<div class='tbl-cell'><span class='badge {badge_cls}'>{stt}</span></div>",
            unsafe_allow_html=True,
        )

        with c5:
            if st.button("Xem", key=f"view_{row['PK_MaSuKien']}", use_container_width=True, type="secondary"):
                st.session_state["event_id"] = row["PK_MaSuKien"]
                st.switch_page("pages/event_detail.py")

    showing = len(page_events)
    st.markdown('<div id="detail-pagination-row">', unsafe_allow_html=True)
    info_col, prev_col, nums_col, next_col = st.columns([4, 1, 4, 1], gap="small")

    with info_col:
        st.markdown(
            f"<div class='pg-info-text'>Hiển thị {showing} trên {total_rows} sự kiện</div>",
            unsafe_allow_html=True,
        )

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

    st.markdown("""
    <script>
        document.querySelectorAll('#detail-pagination-row .page-btn[data-page]').forEach(btn => {
            btn.style.cursor = 'pointer';
            btn.addEventListener('click', function() {
                const page = parseInt(this.dataset.page);
                const hiddenBtn = document.querySelector('button[data-testid*="detail_go_' + page + '"]');
                if (hiddenBtn) hiddenBtn.click();
            });
        });
    </script>
    """, unsafe_allow_html=True)
