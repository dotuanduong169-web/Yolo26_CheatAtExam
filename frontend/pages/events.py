"""Trang Quản lý Sự kiện & Bằng chứng (FR03): Tra cứu nhật ký vi phạm, xem snapshot và xác minh đúng/sai."""

import io
import pandas as pd
import streamlit as st
from utils.notify import notify

from components.evidence_dialog import show_evidence_dialog
from services.event_api import list_session_events, verify_event
from services.history_api import get_all_sessions, get_session_detail, delete_session
from utils.auth_guard import require_auth
from utils.hide_streamlit_sidebar import hide_sidebar
from utils.http import init_session_state
from utils.load_css import load_css
from utils.render_header import render_page_header

# ── Cấu hình trang ──────────────────────────────────────────
st.set_page_config(layout="wide", initial_sidebar_state="collapsed", page_title="Sự kiện phát hiện")

init_session_state()
require_auth()

# ── Styles & Sidebar ────────────────────────────────────────
hide_sidebar()
st.markdown(load_css("styles/sidebar.css"), unsafe_allow_html=True)
st.markdown(load_css("styles/app_theme.css"), unsafe_allow_html=True)
render_page_header("Sự kiện phát hiện", active="events")

# Từ điển ánh xạ nhãn hành vi sang tiếng Việt rõ nghĩa
from utils.status_helpers import (
    get_event_status_badge,
    get_friendly_behavior_label,
    get_session_status_badge,
)


# ── Lấy danh sách phiên thi ─────────────────────────────────
client = st.session_state.client

# ── Xử lý query params thao tác sự kiện ─────────────────────
if "confirm_ev" in st.query_params:
    try:
        c_ev_id = int(st.query_params["confirm_ev"])
        c_raw_label = st.query_params.get("raw_label", "")
        del st.query_params["confirm_ev"]
        if "raw_label" in st.query_params:
            del st.query_params["raw_label"]
        res = verify_event(client, c_ev_id, "dung", c_raw_label)
        if res is not None and res.status_code == 200:
            notify.success(f"Đã xác nhận sự kiện EV-{c_ev_id:02d} là Vi phạm")
            st.rerun()
        else:
            notify.error("Không thể cập nhật trạng thái sự kiện")
    except Exception:
        pass

if "reject_ev" in st.query_params:
    try:
        r_ev_id = int(st.query_params["reject_ev"])
        del st.query_params["reject_ev"]
        res = verify_event(client, r_ev_id, "sai", "Answer_paper")
        if res is not None and res.status_code == 200:
            notify.success(f"Đã bác bỏ sự kiện EV-{r_ev_id:02d} (Báo sai: Giấy thi hợp lệ)")
            st.rerun()
        else:
            notify.error("Không thể cập nhật trạng thái sự kiện")
    except Exception:
        pass

if "select_session" in st.query_params:
    try:
        s_id = int(st.query_params["select_session"])
        del st.query_params["select_session"]
        st.session_state["session_id"] = s_id
        st.session_state["selected_session"] = s_id
        st.rerun()
    except Exception:
        pass

if "view_ev" in st.query_params:
    try:
        target_ev_id = int(st.query_params["view_ev"])
        show_evidence_dialog(target_ev_id)
    except Exception:
        pass

all_sessions = get_all_sessions(client)

if not all_sessions:
    notify.inline("Chưa có ca thi nào được ghi nhận trong cơ sở dữ liệu. Vui lòng khởi tạo ca thi mới tại trang Giám sát trực tiếp để bắt đầu thu thập sự kiện.", kind="info", title="Chưa có dữ liệu ca thi")
    st.stop()

# Tab phân tách: Danh sách sự kiện & Tra cứu lịch sử phiên thi
tab_events, tab_sessions = st.tabs(["Nhật ký sự kiện & Xác minh", "Danh mục ca thi"])

# =========================================================================
# TAB 1: NHẬT KÝ SỰ KIỆN PHÁT HIỆN
# =========================================================================
with tab_events:
    # ── Bộ lọc ──────────────────────────────────────────────
    f_c1, f_c2, f_c3 = st.columns([1.6, 1.2, 1.2])

    with f_c1:
        active_sid = st.session_state.get("session_id")
        session_options = {
            s["PK_MaPhienGiamSat"]: f"Phiên #{s['PK_MaPhienGiamSat']} - {s.get('PhongThi') or 'P.Thi'} ({s.get('MonThi') or 'Môn'})"
            for s in all_sessions
        }

        default_idx = 0
        if active_sid and active_sid in session_options:
            default_idx = list(session_options.keys()).index(active_sid)

        selected_sid = st.selectbox(
            "Chọn phiên giám sát",
            options=list(session_options.keys()),
            format_func=lambda x: session_options.get(x, f"Phiên #{x}"),
            index=default_idx,
        )
        st.session_state["session_id"] = selected_sid

    with f_c2:
        filter_behavior = st.selectbox(
            "Loại hành vi",
            ["Tất cả", "Tài liệu giấy (Cheat_Paper)", "Điện thoại di động (cellphone)", "Quay đầu / Nhìn bài (Head_Turn)"],
        )

    with f_c3:
        filter_status = st.selectbox(
            "Trạng thái kiểm tra",
            ["Tất cả", "Chờ kiểm tra", "Đã xác nhận vi phạm", "Bác bỏ (Báo sai)"],
        )

    # ── Tải danh sách sự kiện ────────────────────────────────
    status_param = ""
    if filter_status == "Chờ kiểm tra":
        status_param = "cho_kiem_tra"
    elif filter_status == "Đã xác nhận vi phạm":
        status_param = "dung"
    elif filter_status == "Bác bỏ (Báo sai)":
        status_param = "sai"

    events = list_session_events(client, selected_sid, trang_thai=status_param, limit=100)

    # Lọc hành vi phía client nếu cần
    if filter_behavior != "Tất cả":
        key_check = "Cheat_Paper" if "Cheat_Paper" in filter_behavior else ("cellphone" if "cellphone" in filter_behavior else "Head_Turn")
        events = [e for e in events if key_check.lower() in (e.get("LoaiHanhVi") or "").lower()]

    st.markdown(f"""
    <div class="wf-box">
        <div class="wf-box-header">
            <div class="wf-box-title">Danh sách sự kiện phát hiện gian lận · Phiên #{selected_sid}</div>
            <div>
                <span class="wf-badge danger">Tổng sự kiện: {len(events)}</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if not events:
        notify.empty_state("Không có sự kiện vi phạm nào", "Không tìm thấy sự kiện nào khớp với tiêu chí lọc hoặc phiên thi này chưa ghi nhận vi phạm gian lận.")
    else:
        # Tiêu đề hàng bảng
        th1, th2, th3, th4, th5, th6, th7 = st.columns([0.8, 1.3, 1.8, 0.8, 1.4, 1.1, 1.8])
        th1.caption("MÃ SỰ KIỆN")
        th2.caption("THỜI GIAN")
        th3.caption("HÀNH VI PHÁT HIỆN")
        th4.caption("ĐỘ TIN CẬY")
        th5.caption("KẾT LUẬN XÁC MINH")
        th6.caption("TRẠNG THÁI")
        th7.markdown('<div style="text-align:right; font-size:11.5px; font-weight:700; color:#64748b; letter-spacing:0.5px;">THAO TÁC</div>', unsafe_allow_html=True)

        st.markdown("<hr style='margin: 4px 0 8px 0; border: none; border-top: 1px solid var(--wf-border);'>", unsafe_allow_html=True)

        for ev in events:
            ev_id = ev.get("PK_MaSuKien")
            raw_label = ev.get("LoaiHanhVi", "?")
            friendly_label = get_friendly_behavior_label(raw_label)
            conf = round(float(ev.get("DoTinCay", 0)) * 100, 1)
            time_str = str(ev.get("ThoiGianPhatHien", ""))[:19].replace("T", " ")
            stt = ev.get("TrangThaiKiemTra", "cho_kiem_tra")
            user_label = ev.get("NhanNguoiDung")
            friendly_user_label = get_friendly_behavior_label(user_label) if user_label else "—"
            stt_badge = get_event_status_badge(stt)

            with st.container():
                c1, c2, c3, c4, c5, c6, c7 = st.columns([0.8, 1.3, 1.8, 0.8, 1.4, 1.1, 1.8])
                with c1:
                    st.markdown(f"<strong>EV-{ev_id:02d}</strong>", unsafe_allow_html=True)
                with c2:
                    st.caption(time_str)
                with c3:
                    st.markdown(f"<span style='color: var(--wf-danger); font-weight: 600;' title='{raw_label}'>{friendly_label}</span>", unsafe_allow_html=True)
                with c4:
                    st.caption(f"{conf}%")
                with c5:
                    if user_label:
                        st.markdown(f"<strong>{friendly_user_label}</strong>", unsafe_allow_html=True)
                    else:
                        st.caption("—")
                with c6:
                    st.markdown(stt_badge, unsafe_allow_html=True)
                with c7:
                    action_html = (
                        f'<div style="display:flex; align-items:center; justify-content:flex-end; gap:6px;">'
                        f'  <a href="/events?view_ev={ev_id}" class="action-svg-btn view-btn" title="Xem nhanh bằng chứng & xác minh vi phạm">'
                        f'    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
                        f'      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8z"/>'
                        f'      <circle cx="12" cy="12" r="3"/>'
                        f'    </svg>'
                        f'  </a>'
                        f'  <a href="/events?confirm_ev={ev_id}&raw_label={raw_label}" class="action-svg-btn confirm-btn" title="Xác nhận đúng vi phạm ({friendly_label})">'
                        f'    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
                        f'      <polyline points="20 6 9 17 4 12"/>'
                        f'    </svg>'
                        f'  </a>'
                        f'  <a href="/events?reject_ev={ev_id}" class="action-svg-btn reject-btn" title="Bác bỏ vi phạm (Báo sai: Giấy thi hợp lệ)">'
                        f'    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
                        f'      <line x1="18" y1="6" x2="6" y2="18"/>'
                        f'      <line x1="6" y1="6" x2="18" y2="18"/>'
                        f'    </svg>'
                        f'  </a>'
                        f'</div>'
                    )
                    st.markdown(action_html, unsafe_allow_html=True)

                st.markdown("<hr style='margin: 4px 0 8px 0; border: none; border-top: 1px solid var(--wf-border);'>", unsafe_allow_html=True)


# =========================================================================
# TAB 2: TRA CỨU DANH MỤC CA THI
# =========================================================================
with tab_sessions:
    st.markdown("""
    <div class="wf-box">
        <div class="wf-box-header">
            <div class="wf-box-title">Danh mục ca thi đã ghi nhận</div>
            <span style="font-size: 11px; color: var(--wf-text-muted);">Quản lý & tra cứu ca thi</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Bộ lọc tìm kiếm ca thi
    s_col1, s_col2 = st.columns([2, 1])
    with s_col1:
        search_kw = st.text_input("Tìm kiếm theo phòng hoặc môn thi", placeholder="Nhập tên phòng hoặc môn thi để lọc...", label_visibility="collapsed")
    with s_col2:
        filter_sess_status = st.selectbox("Trạng thái", ["Tất cả", "Đang giám sát", "Đã kết thúc"], label_visibility="collapsed")

    filtered_sessions = all_sessions
    if search_kw.strip():
        kw = search_kw.strip().lower()
        filtered_sessions = [
            s for s in filtered_sessions
            if kw in (s.get("PhongThi") or "").lower() or kw in (s.get("MonThi") or "").lower() or kw in str(s.get("PK_MaPhienGiamSat", ""))
        ]

    if filter_sess_status == "Đang giám sát":
        filtered_sessions = [s for s in filtered_sessions if not s.get("ThoiGianKetThuc")]
    elif filter_sess_status == "Đã kết thúc":
        filtered_sessions = [s for s in filtered_sessions if s.get("ThoiGianKetThuc")]

    if not filtered_sessions:
        notify.empty_state("Không tìm thấy ca thi nào phù hợp", "Vui lòng thử điều chỉnh lại bộ lọc trạng thái hoặc từ khóa tìm kiếm phòng/môn thi.")
    else:
        # Tiêu đề hàng bảng ca thi
        sh1, sh2, sh3, sh4, sh5 = st.columns([1, 2, 2, 1.2, 1.4])
        sh1.caption("MÃ CA")
        sh2.caption("PHÒNG / MÔN THI")
        sh3.caption("THỜI GIAN")
        sh4.caption("TRẠNG THÁI")
        sh5.markdown('<div style="text-align:right; font-size:11.5px; font-weight:700; color:#64748b; letter-spacing:0.5px;">THAO TÁC</div>', unsafe_allow_html=True)
        st.markdown("<hr style='margin: 4px 0 8px 0; border: none; border-top: 1px solid var(--wf-border);'>", unsafe_allow_html=True)

        for s in filtered_sessions:
            s_id = s.get("PK_MaPhienGiamSat")
            room = s.get("PhongThi") or "Chưa đặt phòng"
            subject = s.get("MonThi") or "Chưa đặt môn"
            start_t = str(s.get("ThoiGianBatDau", ""))[:19].replace("T", " ")
            is_active_sess = not s.get("ThoiGianKetThuc")
            end_t = "Đang diễn ra" if is_active_sess else str(s.get("ThoiGianKetThuc", ""))[:19].replace("T", " ")
            event_count = s.get("so_su_kien", 0)

            status_badge = get_session_status_badge(s.get("TrangThai"), s.get("ThoiGianKetThuc"))

            with st.container():
                sc1, sc2, sc3, sc4, sc5 = st.columns([1, 2, 2, 1.2, 1.4])
                with sc1:
                    st.markdown(f"<strong>Ca #{s_id}</strong>", unsafe_allow_html=True)
                with sc2:
                    st.markdown(f"Phòng: <strong>{room}</strong><br><span style='color: var(--wf-text-muted); font-size:12px;'>Môn: {subject}</span>", unsafe_allow_html=True)
                with sc3:
                    st.caption(f"Bắt đầu: {start_t}<br>Kết thúc: {end_t}", unsafe_allow_html=True)
                with sc4:
                    st.markdown(f"<span class='wf-badge danger'>Sự kiện: {event_count}</span><br>{status_badge}", unsafe_allow_html=True)
                with sc5:
                    action_sess_html = (
                        f'<div style="display:flex; align-items:center; justify-content:flex-end; gap:6px;">'
                        f'  <a href="/session_detail?id={s_id}" class="action-svg-btn view-btn" title="Xem báo cáo chi tiết ca thi #{s_id}">'
                        f'    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
                        f'      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8z"/>'
                        f'      <circle cx="12" cy="12" r="3"/>'
                        f'    </svg>'
                        f'  </a>'
                        f'  <a href="/events?select_session={s_id}" class="action-svg-btn event-btn" title="Xem các sự kiện vi phạm của ca thi này">'
                        f'    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
                        f'      <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>'
                        f'      <path d="M13.73 21a2 2 0 0 1-3.46 0"/>'
                        f'    </svg>'
                        f'  </a>'
                        f'</div>'
                    )
                    st.markdown(action_sess_html, unsafe_allow_html=True)

                st.markdown("<hr style='margin: 4px 0 10px 0; border: none; border-top: 1px solid var(--wf-border);'>", unsafe_allow_html=True)

