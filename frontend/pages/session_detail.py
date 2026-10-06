# -*- coding: utf-8 -*-
"""Trang chi tiết phiên: KPI, biểu đồ tròn và bảng sự kiện."""

import math

import streamlit as st
from utils.notify import notify
import plotly.graph_objects as go

from services.history_api import get_session_detail
from utils.auth_guard import require_auth
from utils.hide_streamlit_sidebar import hide_sidebar
from utils.http import auth_query_params, init_session_state
from utils.load_css import load_css
from utils.render_header import render_page_header
from utils.status_helpers import (
    get_event_status_info,
    get_friendly_behavior_label,
    get_session_status_label,
)

# ── Config ──────────────────────────────────────────────────
st.set_page_config(layout="wide", initial_sidebar_state="collapsed", page_title="Chi tiết phiên")

init_session_state()
require_auth()

if "detail_page" not in st.session_state:
    st.session_state.detail_page = 1

# ── Sidebar & Styles ────────────────────────────────────────
hide_sidebar()
st.markdown(load_css("styles/sidebar.css"), unsafe_allow_html=True)
st.markdown(load_css("styles/app_theme.css"), unsafe_allow_html=True)
st.markdown(load_css("styles/session_detail.css"), unsafe_allow_html=True)

# ── Query params & Session ID (giữ đọc id/p để vào URL trực tiếp) ──
if "id" in st.query_params:
    try:
        st.session_state["selected_session"] = int(st.query_params["id"])
        st.session_state["session_id"] = int(st.query_params["id"])
    except Exception:
        pass

if "p" in st.query_params:
    try:
        st.session_state["detail_page"] = max(1, int(st.query_params["p"]))
    except Exception:
        pass

session_id = st.session_state.get("selected_session") or st.session_state.get("session_id")
if not session_id:
    render_page_header("Chi tiết phiên giám sát", active="history")
    notify.inline("Không tìm thấy mã phiên giám sát cần xem. Vui lòng quay lại danh sách lịch sử ca thi.", kind="warning", title="Thiếu thông tin phiên")
    if st.button("← Quay lại danh mục ca thi", key="btn_back_hist_nosess"):
        st.switch_page("pages/history.py")
    st.stop()


# ── Load Data ───────────────────────────────────────────────
data = get_session_detail(st.session_state.client, session_id)
if not data:
    notify.inline("Không lấy được dữ liệu của phiên giám sát từ máy chủ.", kind="error", title="Lỗi tải dữ liệu")
    st.stop()

sess = data.get("session", {})
events = data.get("events", [])
tong = data.get("tong_su_kien", len(events))
cho_kt = data.get("cho_kiem_tra", 0)
da_xm = data.get("da_xac_minh", tong - cho_kt)
ty_le_sach = data.get("ty_le_sach", 1.0)
room = sess.get("PhongThi") or sess.get("MonThi") or f"#{session_id}"
is_active = (sess.get("TrangThai") == "dang_giam_sat" or not sess.get("ThoiGianKetThuc"))

clean_pct = round(ty_le_sach * 100)
cheat_pct = 100 - clean_pct

# ── Page Header ─────────────────────────────────────────────
render_page_header("Chi tiết lịch sử phiên", active="history")

if st.button("Quay lại danh sách lịch sử", key="btn_back_to_history"):
    st.switch_page("pages/history.py")

status_text = get_session_status_label(sess.get("TrangThai"), sess.get("ThoiGianKetThuc")).upper()
status_cls = "status-running" if is_active else "status-done"

st.markdown(f"""
<div class="page-header" style="margin-top: 10px;">
    <div class="title">Chi tiết ca thi: {room} (Phiên #{session_id})</div>
    <div class="status-badge {status_cls}">{status_text}</div>
</div>
""", unsafe_allow_html=True)

# ── Top Row: Chart + KPI ────────────────────────────────────
col_chart, col_kpi = st.columns([1.1, 2.3], gap="medium")

with col_chart:
    st.markdown('<div class="card-title">Tỉ lệ sạch / gian lận</div>', unsafe_allow_html=True)

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

with col_kpi:
    start = str(sess.get("ThoiGianBatDau", ""))[:16].replace("T", " ")
    end = str(sess.get("ThoiGianKetThuc", "") or "Đang chạy")[:16].replace("T", " ")
    room_name = sess.get("PhongThi") or "—"
    sub_name = sess.get("MonThi") or "Chưa phân môn"

    # Hàng 1: Thông tin ca thi (Phòng / Môn + Thời gian)
    r1_c1, r1_c2 = st.columns(2, gap="small")
    with r1_c1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-card-content">
                <div class="kpi-label">Phòng / Môn thi</div>
                <div class="kpi-value" style="font-size: 22px;">{room_name}</div>
                <div class="kpi-sub green">{sub_name}</div>
            </div>
            <div class="kpi-card-icon purple">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
                    <polyline points="9 22 9 12 15 12 15 22"/>
                </svg>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with r1_c2:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-card-content">
                <div class="kpi-label">Thời gian bắt đầu</div>
                <div class="kpi-value blue" style="font-size: 18px;">{start}</div>
                <div class="kpi-sub">Kết thúc: {end}</div>
            </div>
            <div class="kpi-card-icon blue">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="12" cy="12" r="10"/>
                    <polyline points="12 6 12 12 16 14"/>
                </svg>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Hàng 2: Thống kê vi phạm (Tổng sự kiện + Chờ kiểm tra)
    r2_c1, r2_c2 = st.columns(2, gap="small")
    with r2_c1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-card-content">
                <div class="kpi-label">Tổng sự kiện gian lận</div>
                <div>
                    <span class="kpi-value orange">{tong:02d}</span>
                    <span class="kpi-unit">sự kiện</span>
                </div>
                <div class="kpi-sub {'warn' if tong > 0 else 'green'}">{'Cần kiểm tra' if tong > 0 else 'Đạt chuẩn'}</div>
            </div>
            <div class="kpi-card-icon orange">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
                    <line x1="12" y1="9" x2="12" y2="13"/>
                    <line x1="12" y1="17" x2="12.01" y2="17"/>
                </svg>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with r2_c2:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-card-content">
                <div class="kpi-label">Chờ kiểm tra</div>
                <div>
                    <span class="kpi-value">{cho_kt:02d}</span>
                    <span class="kpi-unit">sự kiện</span>
                </div>
                <div class="kpi-sub">Đã xác minh: {da_xm}</div>
            </div>
            <div class="kpi-card-icon green">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                    <polyline points="22 4 12 14.01 9 11.01"/>
                </svg>
            </div>
        </div>
        """, unsafe_allow_html=True)

# ── Events Table ────────────────────────────────────────────

PAGE_SIZE = 5
total_rows = len(events)
total_pages = max(1, math.ceil(total_rows / PAGE_SIZE))

st.session_state.detail_page = min(st.session_state.detail_page, total_pages)
page = st.session_state.detail_page

start_idx = (page - 1) * PAGE_SIZE
end_idx = start_idx + PAGE_SIZE
page_events = events[start_idx:end_idx]

st.markdown("""
    <div class="table-header" style="margin-top: 18px;">
        <span class="table-title">Danh sách sự kiện vi phạm đã phát hiện</span>
    </div>
""", unsafe_allow_html=True)

if not events:
    notify.empty_state("Phiên thi này không có sự kiện vi phạm nào", "Hệ thống camera AI không phát hiện bất kỳ hành vi nghi vấn gian lận nào trong suốt ca thi này.")
else:
    # Header hàng bảng đồng bộ st.columns đảm bảo thẳng hàng 100% với các hàng dữ liệu
    th1, th2, th3, th4, th5 = st.columns([1.2, 1.4, 0.9, 1.3, 0.8])
    th1.caption("THỜI GIAN")
    th2.caption("HÀNH VI PHÁT HIỆN")
    th3.caption("ĐỘ TIN CẬY")
    th4.caption("TRẠNG THÁI")
    th5.markdown('<div style="text-align:right; font-size:11.5px; font-weight:700; color:#64748b; letter-spacing:0.5px; padding-right:8px;">THAO TÁC</div>', unsafe_allow_html=True)

    st.markdown("<hr style='margin: 4px 0 8px 0; border: none; border-top: 1px solid var(--wf-border);'>", unsafe_allow_html=True)

    aqs = auth_query_params()
    for row in page_events:
        c1, c2, c3, c4, c5 = st.columns([1.2, 1.4, 0.9, 1.3, 0.8])

        c1.markdown(
            f"<div class='tbl-cell'><b>{str(row.get('ThoiGianPhatHien', ''))[:19].replace('T', ' ')}</b></div>",
            unsafe_allow_html=True,
        )

        raw_bh = row.get("LoaiHanhVi", "?")
        friendly_bh = get_friendly_behavior_label(raw_bh)
        c2.markdown(
            f"<div class='tbl-cell'><span style='color: var(--wf-danger); font-weight:600;'>{friendly_bh}</span></div>",
            unsafe_allow_html=True,
        )

        c3.markdown(
            f"<div class='tbl-cell'>{round(float(row.get('DoTinCay', 0)) * 100, 1)}%</div>",
            unsafe_allow_html=True,
        )

        stt = row.get("TrangThaiKiemTra", "cho_kiem_tra")
        stt_lbl, badge_cls = get_event_status_info(stt)
        c4.markdown(
            f"<div class='tbl-cell'><span class='{badge_cls}'>{stt_lbl}</span></div>",
            unsafe_allow_html=True,
        )

        with c5:
            ev_pk = row["PK_MaSuKien"]
            action_html = (
                f'<div style="display:flex; align-items:center; justify-content:flex-end; padding-right:8px; height:100%;">'
                f'  <a href="/event_detail?id={ev_pk}&from_session={session_id}&{aqs}" target="_self" class="action-svg-btn view-btn" title="Xem chi tiết vi phạm #{ev_pk}">'
                f'    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
                f'      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8z"/>'
                f'      <circle cx="12" cy="12" r="3"/>'
                f'    </svg>'
                f'  </a>'
                f'</div>'
            )
            st.markdown(action_html, unsafe_allow_html=True)

        st.markdown("<hr style='margin: 4px 0 8px 0; border: none; border-top: 1px solid var(--wf-border);'>", unsafe_allow_html=True)

    # Phân trang nhỏ gọn Figma Standard
    showing = len(page_events)
    st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)
    pg_left, pg_right = st.columns([1, 1])

    with pg_left:
        st.markdown(
            f"<div style='font-size: 13px; color: #64748b; line-height: 32px; font-weight: 500;'>"
            f"Hiển thị <strong>{start_idx + 1} – {start_idx + showing}</strong> trong tổng số <strong>{total_rows}</strong> sự kiện"
            f"</div>",
            unsafe_allow_html=True,
        )

    with pg_right:
        pag_items = []
        btn_base = "display: inline-flex; align-items: center; justify-content: center; width: 32px; height: 32px; border-radius: 6px; text-decoration: none; font-size: 13px; transition: all 0.2s;"

        if page <= 1:
            pag_items.append(f'<span style="{btn_base} border: 1px solid #e2e8f0; background: #f8fafc; color: #cbd5e1; cursor: not-allowed;">‹</span>')
        else:
            pag_items.append(f'<a href="/session_detail?id={session_id}&{aqs}&p={page - 1}" target="_self" style="{btn_base} border: 1px solid #cbd5e1; background: #ffffff; color: #334155;">‹</a>')

        for p in range(1, total_pages + 1):
            if total_pages > 7 and abs(p - page) > 2 and p != 1 and p != total_pages:
                if p == 2 or p == total_pages - 1:
                    pag_items.append('<span style="display: inline-flex; align-items: center; justify-content: center; width: 18px; height: 32px; color: #94a3b8; font-size: 13px;">…</span>')
                continue
            if p == page:
                pag_items.append(f'<span style="{btn_base} border: 1px solid #2563eb; background: #2563eb; color: #ffffff; font-weight: 700;">{p}</span>')
            else:
                pag_items.append(f'<a href="/session_detail?id={session_id}&{aqs}&p={p}" target="_self" style="{btn_base} border: 1px solid #cbd5e1; background: #ffffff; color: #334155; font-weight: 500;">{p}</a>')

        if page >= total_pages:
            pag_items.append(f'<span style="{btn_base} border: 1px solid #e2e8f0; background: #f8fafc; color: #cbd5e1; cursor: not-allowed;">›</span>')
        else:
            pag_items.append(f'<a href="/session_detail?id={session_id}&{aqs}&p={page + 1}" target="_self" style="{btn_base} border: 1px solid #cbd5e1; background: #ffffff; color: #334155;">›</a>')

        st.markdown(f'<div class="history-pagination" style="display: flex !important; align-items: center !important; justify-content: flex-end !important; gap: 4px !important; width: 100% !important;">{"".join(pag_items)}</div>', unsafe_allow_html=True)



