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
    get_stream_token,
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
from utils.render_header import render_page_header
from utils.status_helpers import get_friendly_behavior_label

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
if not rows:
    notify.info("Ca thi này chưa có thí sinh nào. Vui lòng nhập danh sách thí sinh ở khung phía trên.")
else:
    # ── Chuyển đổi linh hoạt giữa Danh sách giám sát vi phạm và Lưới camera ──
    tab_list, tab_grid = st.tabs([
        f"Danh sách giám sát vi phạm ({alr_cands} nghi vấn)",
        f"Lưới camera thời gian thực ({tot_cands} thí sinh)",
    ])

    # =========================================================================
    # TAB 1: DANH SÁCH GIÁM SÁT VI PHẠM (DỄ THEO DÕI, TẬP TRUNG GIAN LẬN)
    # =========================================================================
    with tab_list:
        f_col1, f_col2 = st.columns([2.2, 1.2], vertical_alignment="center")
        with f_col1:
            list_filter = st.radio(
                "Bộ lọc",
                options=["Tất cả", "Nghi vấn gian lận", "Đang thi bình thường (sạch)"],
                horizontal=True,
                key="online_list_filter_mode",
                label_visibility="collapsed",
            )
        with f_col2:
            st.markdown(
                f"<div style='text-align: right; font-size: 12px; color: #64748b;'>"
                f"Tổng: <strong>{tot_cands}</strong> · Nghi vấn: <strong style='color:#dc2626;'>{alr_cands}</strong> · Online: <strong style='color:#16a34a;'>{act_cands}</strong>"
                f"</div>",
                unsafe_allow_html=True,
            )

        # Sắp xếp danh sách: Thí sinh có nghi vấn/chờ duyệt được ĐẨY LÊN ĐẦU TIÊN
        sorted_rows = sorted(
            rows,
            key=lambda r: (
                -(r.get("cho_kiem_tra", 0) or 0),
                -(r.get("tong_su_kien", 0) or 0),
                -int(bool(r.get("dang_giam_sat"))),
                str(r.get("SBD") or ""),
            ),
        )

        if list_filter == "Nghi vấn gian lận":
            filtered_rows = [
                r for r in sorted_rows
                if (r.get("cho_kiem_tra", 0) or 0) > 0 or (r.get("tong_su_kien", 0) or 0) > 0
            ]
        elif list_filter == "Đang thi bình thường (sạch)":
            filtered_rows = [
                r for r in sorted_rows
                if bool(r.get("dang_giam_sat")) and (r.get("tong_su_kien", 0) or 0) == 0
            ]
        else:
            filtered_rows = sorted_rows

        if not filtered_rows:
            if list_filter == "Nghi vấn gian lận":
                notify.empty_state(
                    "Không có thí sinh nghi vấn gian lận",
                    "Toàn bộ thí sinh trong ca thi đang làm bài nghiêm túc, chưa ghi nhận hành vi vi phạm nào.",
                )
            else:
                notify.empty_state(
                    "Không có thí sinh phù hợp",
                    "Chưa có thí sinh nào khớp với bộ lọc đã chọn.",
                )
        else:
            h1, h2, h3, h4, h5 = st.columns([1.6, 1.2, 1.8, 2.0, 1.0])
            h1.caption("THÍ SINH (SBD / HỌ TÊN)")
            h2.caption("TRẠNG THÁI CAMERA")
            h3.caption("ĐÁNH GIÁ GIAN LẬN")
            h4.caption("HÀNH VI GẦN NHẤT")
            h5.caption("THAO TÁC")
            st.markdown("<hr style='margin: 4px 0 10px 0; border: none; border-top: 1px solid var(--wf-border);'>", unsafe_allow_html=True)

            for r in filtered_rows:
                r1, r2, r3, r4, r5 = st.columns([1.6, 1.2, 1.8, 2.0, 1.0], vertical_alignment="center")
                sbd = html.escape(str(r.get("SBD") or ""))
                hoten = html.escape(str(r.get("HoTen") or "Thí sinh"))
                lop = html.escape(str(r.get("Lop") or ""))
                lop_str = f" · {lop}" if lop else ""
                is_active = bool(r.get("dang_giam_sat"))
                front_active = bool(r.get("camera_front_active"))
                side_active = bool(r.get("camera_side_active"))
                sid = r.get("PK_MaPhienGiamSat")
                cho_kt = r.get("cho_kiem_tra", 0) or 0
                tong_sk = r.get("tong_su_kien", 0) or 0
                has_alert = cho_kt > 0 or tong_sk > 0

                # Cột 1: Thông tin thí sinh
                with r1:
                    st.markdown(
                        f"<div><span style='font-weight:700; font-size:13.5px; color:#0f172a;'>{sbd}</span><br>"
                        f"<span style='font-size:12.5px; color:#475569;'>{hoten}{lop_str}</span></div>",
                        unsafe_allow_html=True,
                    )

                # Cột 2: Trạng thái camera
                with r2:
                    if is_active:
                        cam_f = (
                            '<span class="cand-cam-chip on"><span class="cand-cam-dot on"></span>Trước</span>'
                            if front_active else
                            '<span class="cand-cam-chip"><span class="cand-cam-dot"></span>Trước</span>'
                        )
                        cam_s = (
                            '<span class="cand-cam-chip on"><span class="cand-cam-dot on"></span>Phụ</span>'
                            if side_active else
                            '<span class="cand-cam-chip"><span class="cand-cam-dot"></span>Phụ</span>'
                        )
                        st.markdown(
                            f"<div style='font-size:12px; font-weight:600; color:#16a34a; margin-bottom:4px;'>Đang thi</div>"
                            f"<div style='display:flex; gap:4px; align-items:center;'>{cam_f}{cam_s}</div>",
                            unsafe_allow_html=True,
                        )
                    elif sid:
                        st.markdown(
                            "<div style='font-size:12px; font-weight:600; color:#64748b;'>Đã dừng</div>"
                            "<div style='font-size:11px; color:#94a3b8;'>Đã rời phòng</div>",
                            unsafe_allow_html=True,
                        )
                    else:
                        st.markdown(
                            "<div style='font-size:12px; font-weight:500; color:#94a3b8;'>Chưa vào</div>"
                            "<div style='font-size:11px; color:#94a3b8;'>Chờ kết nối</div>",
                            unsafe_allow_html=True,
                        )

                # Cột 3: Đánh giá gian lận
                with r3:
                    if cho_kt > 0:
                        st.markdown(
                            f"<span class='cand-alert-tag danger' style='display:inline-block;'>Nghi vấn ({cho_kt} chờ duyệt)</span><br>"
                            f"<span style='font-size:11px; color:#dc2626; font-weight:600;'>Tổng {tong_sk} sự kiện vi phạm</span>",
                            unsafe_allow_html=True,
                        )
                    elif tong_sk > 0:
                        st.markdown(
                            f"<span class='cand-alert-tag neutral' style='display:inline-block; border-color:#cbd5e1;'>Có {tong_sk} sự kiện</span><br>"
                            f"<span style='font-size:11px; color:#16a34a; font-weight:500;'>Đã xác minh hết</span>",
                            unsafe_allow_html=True,
                        )
                    elif is_active:
                        st.markdown(
                            f"<span class='cand-alert-tag' style='display:inline-block; background:#f0fdf4; color:#16a34a; border:1px solid #bbf7d0;'>Bình thường (Sạch)</span><br>"
                            f"<span style='font-size:11px; color:#64748b;'>Không có vi phạm</span>",
                            unsafe_allow_html=True,
                        )
                    else:
                        st.markdown(
                            "<span class='cand-alert-tag neutral' style='display:inline-block;'>Chưa vào thi</span>",
                            unsafe_allow_html=True,
                        )

                # Cột 4: Hành vi vi phạm gần nhất
                with r4:
                    raw_bh = r.get("hanh_vi_moi_nhat")
                    bh_time = r.get("thoi_gian_vi_pham")
                    if raw_bh:
                        friendly_bh = get_friendly_behavior_label(raw_bh)
                        time_disp = str(bh_time)[:19].replace("T", " ") if bh_time else "Gần đây"
                        st.markdown(
                            f"<div style='font-size:12.5px; font-weight:600; color:#dc2626;'>{friendly_bh}</div>"
                            f"<div style='font-size:11px; color:#64748b;'>Lúc: {time_disp}</div>",
                            unsafe_allow_html=True,
                        )
                    elif has_alert:
                        st.markdown(
                            "<div style='font-size:12px; font-weight:500; color:#d97706;'>Có sự kiện ghi nhận</div>",
                            unsafe_allow_html=True,
                        )
                    else:
                        st.markdown(
                            "<div style='font-size:12px; color:#94a3b8;'>Không ghi nhận vi phạm</div>",
                            unsafe_allow_html=True,
                        )

                # Cột 5: Thao tác nhanh
                with r5:
                    if sid:
                        if st.button("Chi tiết", key=f"tbl_ev_{r['PK_MaThiSinh']}", use_container_width=True):
                            st.session_state["selected_session"] = sid
                            st.session_state["detail_return_to"] = "online_exam"
                            st.switch_page("pages/session_detail.py")
                    else:
                        st.caption("—")

                st.markdown("<hr style='margin: 4px 0 8px 0; border: none; border-top: 1px solid #f1f5f9;'>", unsafe_allow_html=True)

    # =========================================================================
    # TAB 2: LƯỚI CAMERA THỜI GIAN THỰC (QUAN SÁT VISUAL)
    # =========================================================================
    with tab_grid:
        def _snap_cell(sid, role, active, joined, label, empty_msg, alt_text):
            """Một ô ảnh camera (trước/phụ) trong card thí sinh."""
            if not sid:
                body = '<div class="cand-snap-empty">Chưa vào phòng thi</div>'
            else:
                snap_bytes = get_candidate_snapshot(
                    st.session_state.client, sid, role=role, variant="thumbnail"
                )
                if snap_bytes:
                    b64_snap = base64.b64encode(snap_bytes).decode("ascii")
                    body = f'<img src="data:image/jpeg;base64,{b64_snap}" alt="{alt_text}"/>'
                elif active:
                    body = '<div class="cand-snap-waiting">Đang kết nối camera...</div>'
                elif joined:
                    body = '<div class="cand-snap-waiting">Đã cấp link, chờ kết nối</div>'
                else:
                    body = f'<div class="cand-snap-empty">{empty_msg}</div>'
            dot_cls = " on" if active else ""
            return (
                '<div class="cand-snap-cell">'
                f'<div class="cand-snap-label"><span class="cand-cam-dot{dot_cls}"></span>{label}</div>'
                f'<div class="cand-snap-wrap">{body}</div>'
                '</div>'
            )

        CHUNK_SIZE = 4
        for chunk_idx in range(0, len(rows), CHUNK_SIZE):
            chunk = rows[chunk_idx : chunk_idx + CHUNK_SIZE]
            cols = st.columns(CHUNK_SIZE)
            for col_idx, c in enumerate(chunk):
                with cols[col_idx]:
                    is_active = bool(c.get("dang_giam_sat"))
                    front_active = bool(c.get("camera_front_active"))
                    side_active = bool(c.get("camera_side_active"))
                    side_joined = bool(c.get("camera_side_joined"))
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

                    # Hai camera: webcam máy tính (front) + điện thoại (side)
                    front_cell = _snap_cell(
                        sid, "front", front_active, bool(sid),
                        "Camera trước", "Chưa có ảnh",
                        f"Camera trước {sbd_escaped}",
                    )
                    side_cell = _snap_cell(
                        sid, "side", side_active, side_joined,
                        "Camera phụ", "Chưa kết nối",
                        f"Camera phụ {sbd_escaped}",
                    )
                    snap_html = f'<div class="cand-snap-pair">{front_cell}{side_cell}</div>'

                    cam_chip_front = (
                        '<span class="cand-cam-chip on"><span class="cand-cam-dot on"></span>Trước</span>'
                        if front_active else
                        '<span class="cand-cam-chip"><span class="cand-cam-dot"></span>Trước</span>'
                    )
                    cam_chip_side = (
                        '<span class="cand-cam-chip on"><span class="cand-cam-dot on"></span>Phụ</span>'
                        if side_active else
                        '<span class="cand-cam-chip"><span class="cand-cam-dot"></span>Phụ</span>'
                    )

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
                            <div class="cand-cam-row">{cam_chip_front}{cam_chip_side}</div>
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
