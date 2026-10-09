"""Trang Thi online (FR-online): nhập DS thí sinh, lưới giám thị theo ca thi."""

import base64
import html
import streamlit as st
from streamlit_autorefresh import st_autorefresh

from config import API_BASE_URL
from services.candidate_api import (
    close_session,
    create_online_session,
    exam_overview,
    extract_error_detail,
    get_candidate_snapshot,
    import_candidates,
    list_candidates,
    open_session,
)
from services.history_api import get_history
from utils.auth_guard import require_auth
from utils.hide_streamlit_sidebar import hide_sidebar
from utils.http import cache_invalidate, init_session_state
from utils.load_css import load_css
from utils.notify import notify
from utils.render_page_header import render_page_header if False else None
from utils.render_header import render_page_header

# ── Cấu hình trang ──────────────────────────────────────────
st.set_page_config(layout="wide", initial_sidebar_state="collapsed", page_title="Thi online")

# ── Styles & Header ─────────────────────────────────────────
hide_sidebar()
st.markdown(load_css("styles/sidebar.css"), unsafe_allow_html=True)
st.markdown(load_css("styles/app_theme.css"), unsafe_allow_html=True)
st.markdown(load_css("styles/online_exam.css"), unsafe_allow_html=True)

init_session_state()
require_auth()

render_page_header("Thi online", active="online_exam")

# ── Chọn ca thi (phiên phòng) ───────────────────────────────
sessions = get_history(st.session_state.client, limit=50) or []

# Hỗ trợ tạo nhanh ca thi online mới
with st.expander("Tạo ca thi online mới", expanded=not bool(sessions)):
    col_cr, col_cs, col_cb = st.columns([2, 2, 1])
    with col_cr:
        new_room = st.text_input("Phòng thi", placeholder="VD: P.Online-101", key="new_room_inp")
    with col_cs:
        new_subj = st.text_input("Môn thi", placeholder="VD: Toán học", key="new_subj_inp")
    with col_cb:
        st.write("")
        st.write("")
        if st.button("Tạo ca thi", type="primary", key="btn_create_online"):
            if not (new_room or "").strip() or not (new_subj or "").strip():
                notify.warning("Vui lòng điền đủ phòng thi và môn thi.")
            else:
                resp = create_online_session(st.session_state.client, new_room.strip(), new_subj.strip())
                if resp is not None and resp.status_code == 200:
                    created_data = resp.json()
                    new_id = created_data.get("PK_MaPhienGiamSat")
                    cache_invalidate("hist:")
                    notify.success(f"Đã tạo ca thi #{new_id} ({new_room} - {new_subj}).")
                    st.session_state["online_exam_session"] = new_id
                    st.rerun()
                else:
                    err_msg = extract_error_detail(resp, default="Tạo ca thi thất bại")
                    notify.error(err_msg, title="Lỗi tạo ca thi")

if not sessions:
    notify.info("Chưa có ca thi nào. Bạn hãy tạo ca thi mới ở trên.")
    st.stop()

sess_dict = {s["PK_MaPhienGiamSat"]: s for s in sessions}

if "online_exam_session" in st.session_state and st.session_state["online_exam_session"] not in sess_dict:
    st.session_state["online_exam_session"] = list(sess_dict.keys())[0]


def _format_sess(sid):
    s = sess_dict.get(sid, {})
    stt = s.get("TrangThai")
    stt_text = "Đang mở" if stt == "dang_giam_sat" else "Đã đóng"
    return f"#{sid} - {s.get('PhongThi') or ''} {s.get('MonThi') or ''} ({stt_text})".strip()


# Thẻ quản lý ca thi trực tuyến
col_select, col_action = st.columns([3, 1])
with col_select:
    sel_id = st.selectbox(
        "Ca thi đang chọn",
        options=list(sess_dict.keys()),
        format_func=_format_sess,
        key="online_exam_session",
    )

curr_sess = sess_dict.get(sel_id, {})
is_open = curr_sess.get("TrangThai") == "dang_giam_sat"

with col_action:
    st.write("")
    st.write("")
    if is_open:
        if st.button("Kết thúc ca thi", key=f"btn_close_sess_{sel_id}"):
            res = close_session(st.session_state.client, sel_id)
            if res is not None and res.status_code == 200:
                cache_invalidate("hist:")
                notify.success(f"Đã kết thúc ca thi #{sel_id}.")
                st.rerun()
            else:
                err_msg = extract_error_detail(res, default="Không thể kết thúc ca thi")
                notify.error(err_msg, title="Lỗi kết thúc ca thi")
    else:
        if st.button("Mở ca thi", type="primary", key=f"btn_open_sess_{sel_id}"):
            res = open_session(st.session_state.client, sel_id)
            if res is not None and res.status_code == 200:
                cache_invalidate("hist:")
                notify.success(f"Đã mở ca thi #{sel_id}! Thí sinh có thể vào phòng thi.")
                st.rerun()
            else:
                err_msg = extract_error_detail(res, default="Không thể mở ca thi")
                notify.error(err_msg, title="Lỗi mở ca thi")

# ── Link trang thi cho thí sinh ─────────────────────────────
exam_url = f"{API_BASE_URL}/exam?session_id={sel_id}"
if is_open:
    st.markdown(
        f"""
        <div class="exam-url-container">
            <div class="exam-url-info">
                <div class="exam-url-label">
                    <span class="wf-badge success">Ca thi đang mở</span>
                    <span>Đường dẫn dự thi trực tuyến cho thí sinh</span>
                </div>
                <div>
                    <a href="{exam_url}" target="_blank" class="exam-url-link">{exam_url}</a>
                </div>
            </div>
            <div style="font-size: 12px; color: #64748b; text-align: right;">
                Thí sinh mở link trên trình duyệt và chỉ cần nhập <strong>SBD</strong> để tham gia
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        f"""
        <div class="exam-url-container" style="border-left: 4px solid #d97706; background: #fffdfa;">
            <div class="exam-url-info">
                <div class="exam-url-label">
                    <span class="wf-badge warning">Ca thi đang đóng</span>
                    <span>Đường dẫn dự thi trực tuyến cho thí sinh</span>
                </div>
                <div>
                    <span class="exam-url-link" style="color: #64748b; background: #f1f5f9; border-color: #cbd5e1;">{exam_url}</span>
                </div>
            </div>
            <div style="font-size: 12px; color: #d97706; font-weight: 500; text-align: right;">
                Hãy bấm nút <strong>"Mở ca thi"</strong> ở trên để thí sinh có thể vào phòng
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ── Nhập danh sách thí sinh ─────────────────────────────────
with st.expander("Nhập danh sách thí sinh vào ca thi (SBD, Họ tên, Lớp)", expanded=False):
    st.caption("Mỗi dòng một thí sinh, phân tách bằng dấu phẩy. Ví dụ: `TS001, Nguyễn Văn A, 12A1`")
    raw = st.text_area("Danh sách thí sinh", height=120, key="online_import_text", placeholder="TS001, Nguyễn Văn A, 12A1\nTS002, Trần Thị B, 12A2")
    if st.button("Nhập danh sách thí sinh", type="primary", key="online_import_btn"):
        items = []
        for line in (raw or "").splitlines():
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 2 and parts[0] and parts[1]:
                items.append({
                    "SBD": parts[0],
                    "HoTen": parts[1],
                    "Lop": parts[2] if len(parts) > 2 else None,
                })
        if not items:
            notify.warning("Chưa có dòng hợp lệ nào (yêu cầu tối thiểu SBD và Họ tên).")
        else:
            res = import_candidates(st.session_state.client, sel_id, items)
            if res is not None and res.status_code == 200:
                msg = f"Đã nhập thành công {len(res.json())} thí sinh vào ca #{sel_id}."
                if not is_open:
                    msg += " Hãy bấm 'Mở ca thi' để thí sinh có thể bắt đầu thi."
                notify.success(msg)
                st.rerun()
            else:
                notify.error("Nhập danh sách thí sinh thất bại.")

# ── Tải dữ liệu tổng quan ca thi ────────────────────────────
rows = exam_overview(st.session_state.client, sel_id) or []

# ── Khối thống kê KPI ca thi ────────────────────────────────
tot_cands = len(rows)
act_cands = sum(1 for r in rows if r.get("dang_giam_sat"))
alr_cands = sum(1 for r in rows if (r.get("cho_kiem_tra") or 0) > 0)
stp_cands = sum(1 for r in rows if not r.get("dang_giam_sat") and r.get("PK_MaPhienGiamSat"))
unj_cands = tot_cands - act_cands - stp_cands

alert_card_cls = " alert" if alr_cands > 0 else ""

st.markdown(
    f"""
    <div class="online-kpi-grid">
        <div class="online-kpi-card">
            <div class="online-kpi-label">Tổng thí sinh</div>
            <div class="online-kpi-val blue">{tot_cands}</div>
            <div class="online-kpi-hint">Đã đăng ký trong ca thi</div>
        </div>
        <div class="online-kpi-card">
            <div class="online-kpi-label">Đang thi online</div>
            <div class="online-kpi-val green">{act_cands}</div>
            <div class="online-kpi-hint">Camera AI kết nối thời gian thực</div>
        </div>
        <div class="online-kpi-card{alert_card_cls}">
            <div class="online-kpi-label">Nghi vấn gian lận</div>
            <div class="online-kpi-val red">{alr_cands}</div>
            <div class="online-kpi-hint">Có sự kiện chờ xác minh</div>
        </div>
        <div class="online-kpi-card">
            <div class="online-kpi-label">Đã kết thúc / Chưa vào</div>
            <div class="online-kpi-val">{stp_cands} / {unj_cands}</div>
            <div class="online-kpi-hint">{stp_cands} đã dừng · {unj_cands} chưa vào phòng</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Lưới giám thị ───────────────────────────────────────────
st.markdown(
    f"""
    <div style="display: flex; align-items: center; justify-content: space-between; margin: 20px 0 14px 0;">
        <h3 style="margin: 0; font-size: 17.5px; font-weight: 700; color: #0f172a;">Lưới giám thị thời gian thực</h3>
        <span class="wf-badge accent">{tot_cands} thí sinh</span>
    </div>
    """,
    unsafe_allow_html=True,
)

if not rows:
    notify.info("Ca thi này chưa có thí sinh nào. Vui lòng nhập danh sách thí sinh ở khung phía trên.")
else:
    CHUNK_SIZE = 4
    for chunk_idx in range(0, len(rows), CHUNK_SIZE):
        chunk = rows[chunk_idx : chunk_idx + CHUNK_SIZE]
        cols = st.columns(CHUNK_SIZE)
        for col_idx, c in enumerate(chunk):
            with cols[col_idx]:
                is_active = bool(c.get("dang_giam_sat"))
                sid = c.get("PK_MaPhienGiamSat")
                cho_kt = c.get("cho_kiem_tra", 0) or 0
                tong_sk = c.get("tong_su_kien", 0) or 0
                has_alert = cho_kt > 0

                if is_active:
                    chip_cls = "active"
                    status_text = "Đang thi"
                elif sid:
                    chip_cls = "stopped"
                    status_text = "Đã dừng"
                else:
                    chip_cls = "unjoined"
                    status_text = "Chưa vào"

                violation_cls = " has-violation" if has_alert else ""
                alert_badge_html = (
                    f'<span class="cand-alert-tag danger">{cho_kt} chờ duyệt</span>'
                    if has_alert
                    else '<span class="cand-alert-tag neutral">Bình thường</span>'
                )

                sbd_escaped = html.escape(str(c.get("SBD") or ""))
                hoten_escaped = html.escape(str(c.get("HoTen") or "Thí sinh"))
                lop_val = str(c.get("Lop") or "").strip()
                lop_escaped = f" · {html.escape(lop_val)}" if lop_val else ""

                # Xử lý ảnh snapshot camera
                snap_html = ""
                if sid:
                    snap_bytes = get_candidate_snapshot(st.session_state.client, sid)
                    if snap_bytes:
                        b64_snap = base64.b64encode(snap_bytes).decode("ascii")
                        snap_html = f'<div class="cand-snap-wrap"><img src="data:image/jpeg;base64,{b64_snap}" alt="Snapshot {sbd_escaped}"/></div>'
                    else:
                        if is_active:
                            snap_html = '<div class="cand-snap-wrap"><div class="cand-snap-waiting">Đang kết nối camera...</div></div>'
                        else:
                            snap_html = '<div class="cand-snap-wrap"><div class="cand-snap-empty">Chưa có ảnh vi phạm</div></div>'
                else:
                    snap_html = '<div class="cand-snap-wrap"><div class="cand-snap-empty">Chưa vào phòng thi</div></div>'

                # Render HTML card hoàn chỉnh đồng bộ phong cách
                st.markdown(
                    f"""
                    <div class="cand-card{violation_cls}">
                        <div class="cand-card-header">
                            <div class="cand-meta">
                                <div class="cand-sbd">{sbd_escaped}</div>
                                <div class="cand-name" title="{hoten_escaped}">{hoten_escaped}{lop_escaped}</div>
                            </div>
                            <span class="cand-status-chip {chip_cls}">{status_text}</span>
                        </div>
                        {snap_html}
                        <div class="cand-card-footer">
                            <span>Sự kiện: <strong>{tong_sk}</strong></span>
                            {alert_badge_html}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                if st.button("Chi tiết ca thi", key=f"online_ev_{c['PK_MaThiSinh']}", use_container_width=True):
                    if sid:
                        st.session_state["selected_session"] = sid
                        st.session_state["detail_return_to"] = "online_exam"
                        st.switch_page("pages/session_detail.py")
                    else:
                        notify.info(f"Thí sinh {c.get('HoTen')} ({c.get('SBD')}) chưa vào thi, chưa có dữ liệu phiên.")

st_autorefresh(interval=10000, key="online_grid_refresh")
