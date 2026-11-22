"""Trang Thống kê & Báo cáo (FR05): KPI, phân bố hành vi và timeline cảnh báo
gắn từng thí sinh, kèm ảnh minh chứng + thời gian + trạng thái xác minh."""

import html
import math

import pandas as pd
import plotly.express as px
import streamlit as st
from utils.notify import notify

from services.candidate_api import list_candidates
from services.history_api import get_all_sessions
from services.stats_api import (
    get_behavior_distribution,
    get_candidate_stats,
    get_stats_overview,
    get_stats_summary,
    get_timeline,
)
from utils.auth_guard import require_auth
from utils.hide_streamlit_sidebar import hide_sidebar
from utils.http import init_session_state
from utils.load_css import load_css
from utils.render_header import render_page_header
from utils.status_helpers import get_event_status_info, get_friendly_behavior_label

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

# ── Bộ lọc ca thi / thí sinh ────────────────────────────────
sessions = get_all_sessions(client) or []
sess_map = {0: "Tất cả ca thi"}
for s in sessions:
    sid = s.get("PK_MaPhienGiamSat")
    if sid:
        room = s.get("PhongThi") or "Chưa đặt phòng"
        subject = s.get("MonThi") or "Chưa đặt môn"
        sess_map[sid] = f"#{sid} · {room} · {subject}"

f1, f2, f3 = st.columns([1.5, 1.5, 1.0], vertical_alignment="bottom")
with f1:
    selected_parent = st.selectbox(
        "Ca thi",
        options=list(sess_map.keys()),
        format_func=lambda x: sess_map.get(x, str(x)),
        key="stats_parent_session",
    )
with f2:
    candidate_options = {0: "Tất cả thí sinh"}
    if selected_parent:
        for c in list_candidates(client, selected_parent) or []:
            cid = c.get("PK_MaThiSinh")
            if cid:
                candidate_options[cid] = (
                    f"{c.get('SBD') or ''} · {c.get('HoTen') or ''}"
                    + (f" · {c.get('Lop')}" if c.get("Lop") else "")
                )
    if st.session_state.get("stats_candidate") not in candidate_options:
        st.session_state["stats_candidate"] = 0

    selected_candidate = st.selectbox(
        "Thí sinh",
        options=list(candidate_options.keys()),
        format_func=lambda x: candidate_options.get(x, str(x)),
        key="stats_candidate",
    )
with f3:
    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
    only_alerts = st.checkbox("Chỉ mốc có cảnh báo", value=True, key="stats_only_alerts")

session_filter = selected_parent or None
candidate_filter = selected_candidate or None

# ── Dữ liệu tổng hợp ────────────────────────────────────────
overview = get_stats_overview(client, session_id=session_filter) or {}
summary = get_stats_summary(client)
distribution = get_behavior_distribution(client)
candidate_rows = get_candidate_stats(client, session_id=session_filter) or []
if candidate_filter:
    candidate_rows = [
        r for r in candidate_rows
        if (r.get("candidate") or {}).get("PK_MaThiSinh") == candidate_filter
    ]

total_cheats = summary.get("total_cheats", 0)
if not distribution or all(d.get("count", 0) == 0 for d in distribution):
    # Fallback giữ tương thích dữ liệu cũ: tổng hợp từ timeline nếu có.
    distribution = []

# ── KPI gắn thí sinh (Chuẩn hoá 4 Cards tinh gọn, thiết thực) ──
total_students = overview.get("total_students", len(candidate_rows))
students_alert = overview.get("students_with_alerts", 0)
total_events = overview.get("total_events", total_cheats)
pending_events = overview.get("pending_events", 0)
clean_rate = round(float(overview.get("clean_rate", 1.0)) * 100, 1)

clean_students = max(0, total_students - students_alert)
verified_events = max(0, total_events - pending_events)

alert_color = "#dc2626" if students_alert > 0 else "#16a34a"
event_color = "#d97706" if total_events > 0 else "#0f172a"
clean_color = "#16a34a" if clean_rate == 100.0 else ("#d97706" if clean_rate >= 80.0 else "#dc2626")

st.markdown(
    f"""<div class="wf-grid-4">
<div class="wf-stat-tile">
    <div class="wf-stat-label">Tổng thí sinh</div>
    <div class="wf-stat-num">{total_students}</div>
    <div class="wf-stat-hint">Sĩ số trong ca thi</div>
</div>
<div class="wf-stat-tile">
    <div class="wf-stat-label">Thí sinh có nghi vấn</div>
    <div class="wf-stat-num" style="color:{alert_color};">{students_alert}</div>
    <div class="wf-stat-hint">{"Cần rà soát bằng chứng" if students_alert > 0 else "Không ghi nhận vi phạm"}</div>
</div>
<div class="wf-stat-tile">
    <div class="wf-stat-label">Sự kiện vi phạm</div>
    <div class="wf-stat-num" style="color:{event_color};">{total_events}</div>
    <div class="wf-stat-hint">Chờ duyệt: <strong>{pending_events}</strong> · Đã xử lý: {verified_events}</div>
</div>
<div class="wf-stat-tile">
    <div class="wf-stat-label">Tỷ lệ thí sinh sạch</div>
    <div class="wf-stat-num" style="color:{clean_color};">{clean_rate}%</div>
    <div class="wf-stat-hint">{clean_students}/{total_students} thí sinh nghiêm túc</div>
</div>
</div>""",
    unsafe_allow_html=True,
)

# ── Bảng tổng hợp theo thí sinh ─────────────────────────────
st.markdown("""
<div class="wf-box" style="margin-top: 14px;">
    <div class="wf-box-header">
        <div class="wf-box-title">Tổng hợp cảnh báo theo từng thí sinh</div>
        <span style="font-size: 11px; color: var(--wf-text-muted);">Ảnh và mốc thời gian chi tiết ở timeline bên dưới</span>
    </div>
</div>
""", unsafe_allow_html=True)

if not candidate_rows:
    notify.empty_state(
        "Chưa có thí sinh trong phạm vi lọc",
        "Hãy chọn ca thi đã nhập danh sách thí sinh hoặc chọn 'Tất cả ca thi'.",
    )
else:
    h1, h2, h3, h4, h5, h6 = st.columns([0.8, 1.8, 0.7, 0.8, 0.9, 1.2])
    h1.caption("SBD")
    h2.caption("HỌ TÊN")
    h3.caption("LỚP")
    h4.caption("SỰ KIỆN")
    h5.caption("CHỜ KIỂM TRA")
    h6.caption("LẦN CẢNH BÁO CUỐI")
    st.markdown("<hr style='margin: 4px 0 8px 0; border: none; border-top: 1px solid var(--wf-border);'>", unsafe_allow_html=True)
    for row in candidate_rows[:50]:
        c = row.get("candidate") or {}
        c1, c2, c3, c4, c5, c6 = st.columns([0.8, 1.8, 0.7, 0.8, 0.9, 1.2])
        c1.markdown(f"<strong>{html.escape(str(c.get('SBD') or ''))}</strong>", unsafe_allow_html=True)
        c2.markdown(html.escape(str(c.get("HoTen") or "")), unsafe_allow_html=True)
        c3.caption(c.get("Lop") or "—")
        c4.markdown(f"<span style='color:#dc2626;font-weight:600;'>{row.get('total_events', 0)}</span>", unsafe_allow_html=True)
        c5.caption(str(row.get("pending_events", 0)))
        last_at = row.get("last_alert_at")
        c6.caption(str(last_at)[:19].replace("T", " ") if last_at else "—")
        st.markdown("<hr style='margin: 4px 0 8px 0; border: none; border-top: 1px solid #f1f5f9;'>", unsafe_allow_html=True)

# ── Timeline cảnh báo của tất cả thí sinh ───────────────────
st.markdown("""
<div class="wf-box" style="margin-top: 18px;">
    <div class="wf-box-header">
        <div class="wf-box-title">Timeline cảnh báo · ảnh minh chứng · thời gian · thí sinh</div>
        <span style="font-size: 11px; color: var(--wf-text-muted);">Mỗi mốc có cảnh báo được giữ lại</span>
    </div>
</div>
""", unsafe_allow_html=True)

TIMELINE_PAGE_SIZE = 10
if "stats_timeline_page" not in st.session_state:
    st.session_state.stats_timeline_page = 1
page = st.session_state.stats_timeline_page
skip = (page - 1) * TIMELINE_PAGE_SIZE

timeline = get_timeline(
    client,
    session_id=session_filter,
    candidate_id=candidate_filter,
    only_alerts=only_alerts,
    skip=skip,
    limit=TIMELINE_PAGE_SIZE,
) or {}
items = timeline.get("items", [])
total_tl = int(timeline.get("total", 0) or 0)
total_pages = max(1, math.ceil(total_tl / TIMELINE_PAGE_SIZE))
if page > total_pages:
    st.session_state.stats_timeline_page = total_pages
    page = total_pages


def _status_badge(status: str | None) -> tuple[str, str]:
    """Nhãn trạng thái cho cả event đã xác minh và tick chỉ theo dõi."""
    if status == "theo_doi":
        return "Theo dõi", "wf-badge warning"
    return get_event_status_info(status or "cho_kiem_tra")


if not items:
    notify.empty_state(
        "Chưa có mốc cảnh báo nào",
        "Thử bỏ chọn 'Chỉ mốc có cảnh báo' hoặc chọn ca thi/thí sinh khác.",
    )
else:
    for item in items:
        c = item.get("candidate") or {}
        sess = item.get("session") or {}
        image_b64 = item.get("image_b64")
        ev_id = item.get("event_id")
        camera = "Camera phụ" if item.get("camera") == "side" else "Camera trước"
        status_label, status_cls = _status_badge(item.get("trang_thai"))
        behavior = get_friendly_behavior_label(item.get("hanh_vi") or "")
        conf = item.get("do_tin_cay")
        conf_text = f"{round(float(conf) * 100, 1)}%" if conf is not None else "—"
        time_text = str(item.get("thoi_gian") or "")[:19].replace("T", " ")
        latency = item.get("do_tre_ms")

        img_col, info_col, action_col = st.columns([0.9, 3.6, 0.9], gap="small")
        with img_col:
            if image_b64:
                st.markdown(
                    f'<img src="data:image/jpeg;base64,{image_b64}" '
                    f'style="width:100%;border-radius:8px;border:1px solid #e2e8f0;" '
                    f'alt="Ảnh minh chứng {html.escape(str(c.get("SBD") or ""))}"/>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    '<div style="height:64px;display:flex;align-items:center;justify-content:center;'
                    'background:#f8fafc;border:1px dashed #cbd5e1;border-radius:8px;color:#94a3b8;font-size:11px;">Không có ảnh</div>',
                    unsafe_allow_html=True,
                )
        with info_col:
            st.markdown(
                f"<div style='font-size:12px;color:#64748b;'>{html.escape(time_text)} · {camera}</div>"
                f"<div style='font-size:13.5px;font-weight:700;color:#0f172a;margin-top:2px;'>"
                f"{html.escape(str(c.get('SBD') or ''))} · {html.escape(str(c.get('HoTen') or ''))}"
                f"{' · ' + html.escape(str(c.get('Lop'))) if c.get('Lop') else ''}"
                f"</div>"
                f"<div style='font-size:12.5px;margin-top:2px;'>"
                f"<span style='color:#dc2626;font-weight:600;'>{html.escape(behavior)}</span>"
                f" <span style='color:#64748b;'>· {conf_text}</span>"
                f" <span class='{status_cls}' style='margin-left:4px;'>{status_label}</span>"
                f"</div>"
                f"<div style='font-size:11px;color:#94a3b8;margin-top:2px;'>"
                f"Ca #{sess.get('parent_session_id') or sess.get('PK_MaPhienGiamSat') or '—'}"
                f"{' · độ trễ ' + str(latency) + ' ms' if latency is not None else ''}"
                f"</div>",
                unsafe_allow_html=True,
            )
        with action_col:
            if ev_id:
                if st.button("Chi tiết", key=f"stats_tl_ev_{item.get('PK_MaDong')}", use_container_width=True):
                    st.session_state["event_id"] = ev_id
                    if sess.get("PK_MaPhienGiamSat"):
                        st.session_state["from_session_id"] = sess.get("PK_MaPhienGiamSat")
                        st.session_state["selected_session"] = sess.get("PK_MaPhienGiamSat")
                        st.session_state["session_id"] = sess.get("PK_MaPhienGiamSat")
                    st.switch_page("pages/event_detail.py")
            else:
                st.caption("Chưa tạo sự kiện")
        st.markdown("<hr style='margin: 6px 0 8px 0; border: none; border-top: 1px solid #f1f5f9;'>", unsafe_allow_html=True)

    # Phân trang timeline
    pg_left, pg_right = st.columns([3, 1])
    with pg_left:
        start_no = skip + 1 if total_tl else 0
        end_no = min(skip + len(items), total_tl)
        st.markdown(
            f"<div style='font-size:13px;color:#64748b;font-weight:500;'>"
            f"Hiển thị <strong>{start_no} – {end_no}</strong> trong <strong>{total_tl}</strong> mốc cảnh báo"
            f"</div>",
            unsafe_allow_html=True,
        )
    with pg_right:
        nav1, nav2, nav3 = st.columns(3, gap="small")
        with nav1:
            if st.button("‹", key="stats_tl_prev", disabled=(page <= 1)):
                st.session_state.stats_timeline_page = page - 1
                st.rerun()
        with nav2:
            st.markdown(
                f"<div style='text-align:center;line-height:32px;font-size:12px;color:#64748b;'>{page}/{total_pages}</div>",
                unsafe_allow_html=True,
            )
        with nav3:
            if st.button("›", key="stats_tl_next", disabled=(page >= total_pages)):
                st.session_state.stats_timeline_page = page + 1
                st.rerun()

# ── Biểu đồ phân bố hành vi gian lận ────────────────────────
st.markdown("""
<div class="wf-box" style="margin-top: 18px;">
    <div class="wf-box-header">
        <div class="wf-box-title">Biểu đồ phân bố hành vi gian lận thực tế</div>
        <span style="font-size: 11px; color: var(--wf-text-muted);">Tổng hợp từ các sự kiện được camera AI ghi nhận</span>
    </div>
</div>
""", unsafe_allow_html=True)

if not distribution or all(d.get("count", d.get("so_luot", 0)) == 0 for d in distribution):
    notify.empty_state(
        "Chưa có dữ liệu vi phạm gian lận",
        "Chưa có hành vi gian lận nào được hệ thống camera AI ghi nhận trong cơ sở dữ liệu để vẽ biểu đồ phân bố.",
    )
else:
    chart_rows = []
    for d in distribution:
        bh_label = d.get("behavior_name") or d.get("ten_hien_thi") or get_friendly_behavior_label(
            d.get("behavior_code", d.get("loai_hanh_vi", ""))
        )
        chart_rows.append({
            "Hành vi vi phạm": bh_label,
            "Số lượt phát hiện": d.get("count", d.get("so_luot", 0)),
            "Tỷ lệ (%)": d.get("percentage", d.get("ty_le", 0.0)),
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
