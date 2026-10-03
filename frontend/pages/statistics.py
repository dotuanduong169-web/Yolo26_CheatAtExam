"""Trang Thống kê & Báo cáo (FR05): Tổng hợp số liệu vi phạm, phân bố hành vi gian lận và xuất báo cáo."""

import pandas as pd
import plotly.express as px
import streamlit as st
from utils.notify import notify

from services.history_api import get_all_sessions
from services.stats_api import get_stats_summary, get_behavior_distribution
from utils.auth_guard import require_auth
from utils.hide_streamlit_sidebar import hide_sidebar
from utils.http import init_session_state
from utils.load_css import load_css
from utils.render_header import render_page_header
from utils.status_helpers import get_friendly_behavior_label

# ── Cấu hình trang ──────────────────────────────────────────
st.set_page_config(layout="wide", initial_sidebar_state="collapsed", page_title="Báo cáo thống kê")

init_session_state()
require_auth()

# ── Styles & Sidebar ────────────────────────────────────────
hide_sidebar()
st.markdown(load_css("styles/sidebar.css"), unsafe_allow_html=True)
st.markdown(load_css("styles/app_theme.css"), unsafe_allow_html=True)
render_page_header("Báo cáo thống kê", active="statistics")

client = st.session_state.client

# ── Tải dữ liệu thực tế từ backend ──────────────────────────
summary = get_stats_summary(client)
sessions = get_all_sessions(client)
distribution = get_behavior_distribution(client)

total_cheats = summary.get("tong_vi_pham", 0)
clean_rate = round(float(summary.get("ty_le_sach", 1.0)) * 100, 1)
total_sessions = summary.get("tong_ca_thi", len(sessions))

# Tìm hành vi phổ biến nhất từ phân bố thực tế
top_behavior_name = "Chưa có vi phạm"
top_behavior_hint = "Hệ thống hoạt động ổn định"
if distribution:
    top_item = max(distribution, key=lambda x: x.get("so_luot", 0))
    if top_item.get("so_luot", 0) > 0:
        raw_top_bh = top_item.get("loai_hanh_vi", "Gian lận")
        top_behavior_name = top_item.get("ten_hien_thi") or get_friendly_behavior_label(raw_top_bh)
        pct = top_item.get("ty_le", 0)
        cnt = top_item.get("so_luot", 0)
        top_behavior_hint = f"Ghi nhận {cnt} lượt ({pct}%)"

# ── 3 Thẻ chỉ số cốt lõi (Wireframe Grid-3) ──────────────────
st.markdown(f"""
<div class="wf-grid-3">
    <div class="wf-stat-tile">
        <div class="wf-stat-label">Tổng số vi phạm ghi nhận thực tế</div>
        <div class="wf-stat-num">{total_cheats} ca</div>
        <div class="wf-stat-hint">Ghi nhận qua {total_sessions} ca thi trong cơ sở dữ liệu</div>
    </div>
    <div class="wf-stat-tile">
        <div class="wf-stat-label">Tỷ lệ phòng thi đạt chuẩn sạch</div>
        <div class="wf-stat-num">{clean_rate}%</div>
        <div class="wf-stat-hint">Dựa trên tỷ lệ số phiên không phát hiện gian lận</div>
    </div>
    <div class="wf-stat-tile">
        <div class="wf-stat-label">Hành vi vi phạm phổ biến nhất</div>
        <div class="wf-stat-num">{top_behavior_name}</div>
        <div class="wf-stat-hint">{top_behavior_hint}</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Biểu đồ phân bố hành vi gian lận ────────────────────────
st.markdown("""
<div class="wf-box">
    <div class="wf-box-header">
        <div class="wf-box-title">Biểu đồ phân bố hành vi gian lận thực tế</div>
        <span style="font-size: 11px; color: var(--wf-text-muted);">Tổng hợp từ các sự kiện được camera AI ghi nhận</span>
    </div>
</div>
""", unsafe_allow_html=True)

if not distribution or all(d.get("so_luot", 0) == 0 for d in distribution):
    notify.info("Chưa có vi phạm gian lận nào được ghi nhận trong cơ sở dữ liệu để vẽ biểu đồ phân bố.")
else:
    chart_rows = []
    for d in distribution:
        bh_label = d.get("ten_hien_thi") or get_friendly_behavior_label(d.get("loai_hanh_vi", ""))
        chart_rows.append({
            "Hành vi vi phạm": bh_label,
            "Số lượt phát hiện": d.get("so_luot", 0),
            "Tỷ lệ (%)": d.get("ty_le", 0.0),
        })

    chart_data = pd.DataFrame(chart_rows)

    fig = px.bar(
        chart_data,
        x="Hành vi vi phạm",
        y="Số lượt phát hiện",
        text="Số lượt phát hiện",
        color="Hành vi vi phạm",
        color_discrete_sequence=["#2563eb", "#dc2626", "#d97706", "#7c3aed"],
    )

    fig.update_layout(
        height=360,
        margin=dict(l=20, r=20, t=20, b=20),
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        showlegend=False,
        xaxis_title=None,
        yaxis_title="Số lượt phát hiện",
        font=dict(family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto", size=12),
    )
    fig.update_traces(textposition="outside")

    st.plotly_chart(fig, use_container_width=True)


