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
all_sessions = get_all_sessions(client)

if not all_sessions:
    notify.info("Chưa có phiên thi nào được ghi nhận trong cơ sở dữ liệu.")
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
        notify.info("Không có sự kiện nào khớp với tiêu chí lọc.")
    else:
        # Tiêu đề hàng bảng
        th1, th2, th3, th4, th5, th6, th7 = st.columns([0.8, 1.3, 1.8, 0.8, 1.4, 1.1, 1.8])
        th1.caption("MÃ SỰ KIỆN")
        th2.caption("THỜI GIAN")
        th3.caption("HÀNH VI PHÁT HIỆN")
        th4.caption("ĐỘ TIN CẬY")
        th5.caption("KẾT LUẬN XÁC MINH")
        th6.caption("TRẠNG THÁI")
        th7.caption("THAO TÁC")

        st.markdown("<hr style='margin: 4px 0 8px 0; border: none; border-top: 1px solid var(--wf-border);'>", unsafe_allow_html=True)

        for ev in events:
            ev_id = ev.get("PK_MaSuKien")
            raw_label = ev.get("LoaiHanhVi", "?")
            friendly_label = get_friendly_behavior_label(raw_label)
            conf = round(float(ev.get("DoTinCay", 0)) * 100, 1)
            time_str = str(ev.get("ThoiGianPhatHien", ""))[:19]
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
                    act1, act2, act3 = st.columns(3)
                    with act1:
                        if st.button("Xem", key=f"view_ev_{ev_id}", help="Xem chi tiết & xác minh lại nhãn đúng"):
                            show_evidence_dialog(ev_id)
                    with act2:
                        if st.button("Đúng", key=f"confirm_ev_{ev_id}", help="Xác nhận đúng vi phạm"):
                            res = verify_event(client, ev_id, "dung", raw_label)
                            if res is not None and res.status_code == 200:
                                notify.success(f"Đã xác nhận sự kiện EV-{ev_id:02d} là Vi phạm ({friendly_label})")
                                st.rerun()
                            else:
                                notify.error("Không thể cập nhật trạng thái sự kiện")
                    with act3:
                        if st.button("Sai", key=f"reject_ev_{ev_id}", help="Bác bỏ vi phạm (Báo sai: Giấy thi hợp lệ)"):
                            res = verify_event(client, ev_id, "sai", "Answer_paper")
                            if res is not None and res.status_code == 200:
                                notify.success(f"Đã bác bỏ sự kiện EV-{ev_id:02d} (Báo sai: Giấy thi hợp lệ)")
                                st.rerun()
                            else:
                                notify.error("Không thể cập nhật trạng thái sự kiện")

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
        notify.info("Không tìm thấy ca thi nào phù hợp với điều kiện tìm kiếm.")
    else:
        for s in filtered_sessions:
            s_id = s.get("PK_MaPhienGiamSat")
            room = s.get("PhongThi") or "Chưa đặt phòng"
            subject = s.get("MonThi") or "Chưa đặt môn"
            start_t = str(s.get("ThoiGianBatDau", ""))[:19]
            is_active_sess = not s.get("ThoiGianKetThuc")
            end_t = "Đang diễn ra" if is_active_sess else str(s.get("ThoiGianKetThuc", ""))[:19]
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
                    btn_detail_col, btn_select_col = st.columns(2)
                    with btn_detail_col:
                        if st.button("Xem chi tiết", key=f"btn_detail_sess_{s_id}", help="Xem báo cáo và biểu đồ chi tiết của ca này"):
                            st.session_state["selected_session"] = s_id
                            st.switch_page("pages/session_detail.py")
                    with btn_select_col:
                        if st.button("Xem sự kiện", key=f"btn_events_sess_{s_id}", help="Xem các vi phạm của ca này"):
                            st.session_state["session_id"] = s_id
                            st.session_state["selected_session"] = s_id
                            st.rerun()

                st.markdown("<hr style='margin: 4px 0 10px 0; border: none; border-top: 1px solid var(--wf-border);'>", unsafe_allow_html=True)

