"""Trang thống kê hệ thống: xu hướng 7 ngày qua.
Luồng chính: tải thống kê ngày -> lọc 7 ngày -> tính biến động so với hôm qua -> vẽ thẻ KPI và biểu đồ cột."""

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

from components.app_sidebar import render_sidebar
from services.stats_api import get_daily_stats
from utils.auth_guard import require_auth
from utils.hide_streamlit_sidebar import hide_sidebar
from utils.http import init_session_state
from utils.load_css import load_css
from utils.render_header import render_page_header

# ── Cấu hình trang ────────────────────────────────────────
st.set_page_config(layout="wide", page_title="Thống kê")

init_session_state()
require_auth()

# ── CSS và thanh bên ──────────────────────────────────────
st.markdown(load_css("styles/sidebar.css"), unsafe_allow_html=True)
st.markdown(load_css("styles/statistics.css"), unsafe_allow_html=True)
hide_sidebar()
render_sidebar(active="statistics")


# ── Tải dữ liệu ───────────────────────────────────────────
client = st.session_state.client
daily_data = get_daily_stats(client)

if not daily_data:
    # ── Tiêu đề trang ─────────────────────────────────────────
    render_page_header("Thống kê hệ thống")
    st.info("📊 Chưa có dữ liệu thống kê")
    st.stop()

df = pd.DataFrame(daily_data)
df["date"] = pd.to_datetime(df["date"])
df = df.sort_values("date")

# ── Lọc 7 ngày gần nhất ───────────────────────────────────
seven_days_ago = datetime.now() - timedelta(days=7)
df_7d = df[df["date"] >= seven_days_ago]

if len(df_7d) == 0:
    # ── Tiêu đề trang ─────────────────────────────────────────
    render_page_header("Thống kê hệ thống")
    st.info("📊 Chưa có dữ liệu trong 7 ngày gần đây")
    st.stop()

latest = df_7d.iloc[-1]
total = int(latest["total"])
sleeping = int(latest["sleeping"])
focus_rate = latest.get("focus_rate", 0)
normal = total - sleeping

# ── Tính biến động so với hôm qua ─────────────────────────
change_total = "+0%"
change_sleep = "+0%"
change_normal = "+0%"
change_focus = "+0%"

if len(df_7d) > 1:
    yesterday = df_7d.iloc[-2]
    prev_total = int(yesterday.get("total", 0))
    prev_sleeping = int(yesterday.get("sleeping", 0))
    prev_normal = prev_total - prev_sleeping
    prev_focus = yesterday.get("focus_rate", 0)
    
    if prev_total > 0:
        pct = ((total - prev_total) / prev_total * 100)
        change_total = f"{pct:+.0f}%"
    if prev_sleeping > 0:
        pct = ((sleeping - prev_sleeping) / prev_sleeping * 100)
        change_sleep = f"{pct:+.0f}%"
    if prev_normal > 0:
        pct = ((normal - prev_normal) / prev_normal * 100)
        change_normal = f"{pct:+.0f}%"
    if prev_focus and prev_focus > 0:
        pct = ((focus_rate - prev_focus) / prev_focus * 100)
        change_focus = f"{pct:+.0f}%"

sleep_pct = (sleeping / total * 100) if total > 0 else 0
focus_pct = focus_rate * 100 if isinstance(focus_rate, (int, float)) else 0

# ── Tiêu đề trang ─────────────────────────────────────────
render_page_header("Thống kê hệ thống")

# ── Thẻ KPI ───────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4, gap="medium")


def _kpi(col, title, value, change, bar_color, bar_pct=100):
    """Vẽ một thẻ chỉ số KPI."""
    # Xác định màu tăng/giảm theo chuỗi biến động
    if change.startswith("+") and change != "+0%":
        change_cls = "change-up"
    elif change.startswith("-"):
        change_cls = "change-down"
    else:
        change_cls = "change-neutral"

    col.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-header">
            <span class="kpi-label">{title}</span>
            <span class="kpi-change {change_cls}">{change}</span>
        </div>
        <div class="kpi-value">{value}</div>
        <div class="kpi-bar-track">
            <div class="kpi-bar {bar_color}" style="width:{bar_pct}%"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)


_kpi(col1, "Tổng số lớp học", total, change_total, "bar-blue")
_kpi(col2, "Video phân tích", sleeping, change_sleep, "bar-green", sleep_pct)
_kpi(col3, "Ảnh trích xuất", normal, change_normal, "bar-red")
_kpi(col4, "Sinh viên phát hiện", f"{focus_pct:.0f}%", change_focus, "bar-blue", focus_pct)

# ── Băng cảnh báo buồn ngủ ─────────────────────────────────
if sleeping > 0:
    st.markdown(f"""
    <div class="alert-banner">
        <div class="alert-content">
            <span class="alert-icon">⚠️</span>
            <div>
                <div class="alert-title">Cảnh báo hành vi buồn ngủ</div>
                <div class="alert-desc">{sleeping} ca được phát hiện
                    {f'({change_sleep} so với hôm qua)' if len(df_7d) > 1 else ''}</div>
            </div>
        </div>
        <div class="alert-btn">Xem chi tiết</div>
    </div>
    """, unsafe_allow_html=True)

# ── Biểu đồ xu hướng ──────────────────────────────────────
st.markdown("""
<div class="chart-card">
    <div class="chart-header">
        <div>
            <div class="chart-title">Xu hướng ngủ gật</div>
            <div class="chart-subtitle">Phân tích trong 7 ngày qua</div>
        </div>
        <div class="chart-legend">
            <span class="legend-dot"></span> Buồn ngủ
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

if not df_7d.empty:
    df_7d = df_7d.copy()
    day_names = {0: "T2", 1: "T3", 2: "T4", 3: "T5", 4: "T6", 5: "T7", 6: "CN"}
    df_7d["day_label"] = df_7d["date"].dt.dayofweek.map(day_names)

    fig = px.bar(df_7d, x="day_label", y="sleeping", text="sleeping")
    fig.update_traces(
        marker_color="#fb7185",
        marker_line_width=0,
        textposition="outside",
        textfont=dict(size=13, color="#374151", weight=700),
    )
    fig.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(color="#64748b", size=12),
        xaxis=dict(
            title="",
            tickfont=dict(size=13, color="#94a3b8"),
            showgrid=False,
        ),
        yaxis=dict(
            title="",
            showgrid=True,
            gridcolor="#f1f5f9",
            gridwidth=1,
        ),
        bargap=0.35,
        margin=dict(l=20, r=20, t=10, b=30),
        height=320,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
else:
    st.write("Chưa có dữ liệu")