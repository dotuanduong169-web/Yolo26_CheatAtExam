"""Trang Quản lý Sự kiện & Bằng chứng (FR03): Tra cứu nhật ký vi phạm, xem snapshot và xác minh đúng/sai."""

import io
import pandas as pd
import streamlit as st

from components.app_sidebar import render_sidebar
from components.evidence_dialog import show_evidence_dialog
from services.event_api import list_session_events
from services.history_api import get_all_sessions, get_session_detail, delete_session
from utils.auth_guard import require_auth
from utils.hide_streamlit_sidebar import hide_sidebar
from utils.http import init_session_state
from utils.load_css import load_css
from utils.render_header import render_page_header

# ── Cấu hình trang ──────────────────────────────────────────
st.set_page_config(layout="wide", page_title="Sự kiện phát hiện")

init_session_state()
require_auth()

# ── Styles & Sidebar ────────────────────────────────────────
hide_sidebar()
render_sidebar(active="events")
st.markdown(load_css("styles/sidebar.css"), unsafe_allow_html=True)
st.markdown(load_css("styles/app_theme.css"), unsafe_allow_html=True)
render_page_header("Sự kiện phát hiện")

# ── Lấy danh sách phiên thi ─────────────────────────────────
client = st.session_state.client
all_sessions = get_all_sessions(client)

if not all_sessions:
    st.info("Chưa có phiên thi nào được ghi nhận trong cơ sở dữ liệu.")
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
        # Tùy chọn phiên thi
        active_sid = st.session_state.get("session_id")
        session_options = {s["PK_MaPhienGiamSat"]: f"Phiên #{s['PK_MaPhienGiamSat']} - {s.get('PhongThi') or 'P.Thi'} ({s.get('MonThi') or 'Môn'})" for s in all_sessions}
        
        default_idx = 0
        if active_sid and active_sid in session_options:
            default_idx = list(session_options.keys()).index(active_sid)

        selected_sid = st.selectbox(
            "Chọn phiên giám sát",
            options=list(session_options.keys()),
            format_func=lambda x: session_options.get(x, f"Phiên #{x}"),
            index=default_idx,
        )

    with f_c2:
        filter_behavior = st.selectbox(
            "Loại hành vi",
            ["Tất cả", "Cheat_Paper (Tài liệu)", "cellphone (Điện thoại)", "Head_Turn (Quay đầu)"]
        )

    with f_c3:
        filter_status = st.selectbox(
            "Trạng thái kiểm tra",
            ["Tất cả", "Chờ kiểm tra", "Đã xác nhận vi phạm", "Bác bỏ (Báo sai)"]
        )

    # ── Tải danh sách sự kiện ────────────────────────────────
    status_param = None
    if filter_status == "Chờ kiểm tra":
        status_param = "cho_kiem_tra"
    elif filter_status == "Đã xác nhận vi phạm":
        status_param = "dung"
    elif filter_status == "Bác bỏ (Báo sai)":
        status_param = "sai"

    events = list_session_events(client, selected_sid, trang_thai=status_param or "", limit=100)

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
        st.info("Không có sự kiện nào khớp với tiêu chí lọc.")
    else:
        # Tiêu đề hàng bảng (Đồng bộ font/màu mặc định của bảng)
        th1, th2, th3, th4, th5, th6, th7 = st.columns([0.9, 1.6, 1.8, 0.9, 1.5, 1.2, 1.3])
        th1.caption("MÃ SỰ KIỆN")
        th2.caption("THỜI GIAN")
        th3.caption("NHÃN AI")
        th4.caption("ĐỘ TIN CẬY")
        th5.caption("NHÃN XÁC MINH")
        th6.caption("TRẠNG THÁI")
        th7.caption("HÀNH ĐỘNG")

        st.markdown("<hr style='margin: 4px 0 8px 0; border: none; border-top: 1px solid var(--wf-border);'>", unsafe_allow_html=True)

        # Hiển thị dạng bảng trực quan với 3 nút icon button chuẩn nghiệp vụ (theo kiểu ảnh 1)
        from services.event_api import verify_event
        for ev in events:
            ev_id = ev.get("PK_MaSuKien")
            label = ev.get("LoaiHanhVi", "?")
            conf = round(float(ev.get("DoTinCay", 0)) * 100, 1)
            time_str = str(ev.get("ThoiGianPhatHien", ""))[:19]
            stt = ev.get("TrangThaiKiemTra", "cho_kiem_tra")
            user_label = ev.get("NhanNguoiDung")

            stt_badge = {
                "cho_kiem_tra": '<span class="wf-badge warning">Chờ kiểm tra</span>',
                "dung": '<span class="wf-badge success">Xác nhận</span>',
                "sai": '<span class="wf-badge danger">Bác bỏ</span>',
            }.get(stt, f'<span class="wf-badge">{stt}</span>')

            with st.container():
                c1, c2, c3, c4, c5, c6, c7 = st.columns([0.9, 1.6, 1.8, 0.9, 1.5, 1.2, 1.3])
                with c1:
                    st.markdown(f"<strong>EV-{ev_id:02d}</strong>", unsafe_allow_html=True)
                with c2:
                    st.caption(time_str)
                with c3:
                    st.markdown(f"<span style='color: var(--wf-danger); font-weight: 600;'>{label}</span>", unsafe_allow_html=True)
                with c4:
                    st.caption(f"{conf}%")
                with c5:
                    if user_label:
                        st.markdown(f"<strong>{user_label}</strong>", unsafe_allow_html=True)
                    else:
                        st.caption("—")
                with c6:
                    st.markdown(stt_badge, unsafe_allow_html=True)
                with c7:
                    # 3 Icon Button chuẩn nghiệp vụ: Xem ảnh & xác minh (Eye), Xác nhận vi phạm (Check), Bác bỏ (Cross)
                    act1, act2, act3 = st.columns(3)
                    with act1:
                        if st.button("👁", key=f"view_ev_{ev_id}", help="Xem chi tiết & xác minh lại nhãn đúng"):
                            show_evidence_dialog(ev_id)
                    with act2:
                        if st.button("✓", key=f"confirm_ev_{ev_id}", help="Xác nhận đúng vi phạm"):
                            verify_event(client, ev_id, "dung", label)
                            st.toast(f"Đã xác nhận sự kiện EV-{ev_id:02d} là Vi phạm ({label})")
                            st.rerun()
                    with act3:
                        if st.button("✕", key=f"reject_ev_{ev_id}", help="Bác bỏ vi phạm (Báo sai: Giấy thi hợp lệ)"):
                            verify_event(client, ev_id, "sai", "Answer_paper")
                            st.toast(f"Đã bác bỏ sự kiện EV-{ev_id:02d} (Báo sai)")
                            st.rerun()

                st.markdown("<hr style='margin: 4px 0 8px 0; border: none; border-top: 1px solid var(--wf-border);'>", unsafe_allow_html=True)


# =========================================================================
# TAB 2: TRA CỨU DANH MỤC CA THI
# =========================================================================
with tab_sessions:
    st.markdown("""
    <div class="wf-box">
        <div class="wf-box-header">
            <div class="wf-box-title">Danh mục ca thi đã ghi nhận</div>
            <span style="font-size: 11px; color: var(--wf-text-muted);">Lịch sử giám sát</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    for s in all_sessions:
        s_id = s.get("PK_MaPhienGiamSat")
        room = s.get("PhongThi") or "Chưa đặt"
        subject = s.get("MonThi") or "Chưa đặt"
        start_t = str(s.get("ThoiGianBatDau", ""))[:19]
        end_t = str(s.get("ThoiGianKetThuc", "Đang diễn ra"))[:19] if s.get("ThoiGianKetThuc") else "Đang diễn ra"
        event_count = s.get("so_su_kien", 0)

        with st.container():
            sc1, sc2, sc3, sc4, sc5 = st.columns([1, 2, 2, 1.2, 1.2])
            with sc1:
                st.markdown(f"<strong>Ca #{s_id}</strong>", unsafe_allow_html=True)
            with sc2:
                st.markdown(f"Phòng: <strong>{room}</strong> | Môn: <strong>{subject}</strong>", unsafe_allow_html=True)
            with sc3:
                st.caption(f"{start_t} → {end_t}")
            with sc4:
                st.markdown(f"<span class='wf-badge'>Sự kiện: {event_count}</span>", unsafe_allow_html=True)
            with sc5:
                if st.button("Chi tiết ca", key=f"btn_session_{s_id}", use_container_width=True):
                    st.session_state["session_id"] = s_id
                    st.rerun()
            st.markdown("<hr style='margin: 4px 0 10px 0; border: none; border-top: 1px solid var(--wf-border);'>", unsafe_allow_html=True)
