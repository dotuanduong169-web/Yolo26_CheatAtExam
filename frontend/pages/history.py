# -*- coding: utf-8 -*-
"""Trang Lịch sử giám sát (FR03): Gồm 2 tab con Danh mục ca thi & Nhật ký sự kiện gian lận."""

import streamlit as st
from utils.notify import notify

from components.evidence_dialog import show_evidence_dialog
from services.event_api import list_all_events, list_session_events, verify_event
from services.history_api import (
    delete_session,
    get_all_sessions,
    get_history,
    get_history_summary,
)
from utils.auth_guard import require_auth
from utils.hide_streamlit_sidebar import hide_sidebar
from utils.http import init_session_state
from utils.load_css import load_css
from utils.render_header import render_page_header
from utils.status_helpers import (
    get_event_status_badge,
    get_friendly_behavior_label,
    get_session_status_badge,
)

# ── Config ──────────────────────────────────────────────────
st.set_page_config(layout="wide", initial_sidebar_state="collapsed", page_title="Lịch sử giám sát")

st.markdown(load_css("styles/sidebar.css"), unsafe_allow_html=True)
st.markdown(load_css("styles/app_theme.css"), unsafe_allow_html=True)
st.markdown(load_css("styles/history.css"), unsafe_allow_html=True)

init_session_state()
require_auth()
hide_sidebar()
render_page_header("Lịch sử giám sát", active="history")

PAGE_SIZE = 5
client = st.session_state.client

# ── Dialogs & Thao tác nghiệp vụ ───────────────────────────
def handle_delete(session_id: int) -> None:
    """Xóa phiên và hiện kết quả."""
    res = delete_session(client, session_id)
    if not res:
        notify.error("Không thể kết nối đến máy chủ.")
        return
    if res.status_code == 200:
        notify.success(f"Đã xóa phiên giám sát #{session_id} thành công.")
        st.rerun()
    elif res.status_code == 400:
        notify.error("Không thể xóa phiên đang diễn ra.")
    elif res.status_code == 404:
        notify.error("Không tìm thấy phiên giám sát.")
    else:
        notify.error(f"Lỗi hệ thống: {res.text}")


@st.dialog("Xác nhận xóa phiên giám sát")
def confirm_delete_dialog(session_id: int):
    notify.inline(
        f"Bạn có chắc chắn muốn xóa phiên giám sát <strong>#{session_id}</strong>? Toàn bộ sự kiện và hình ảnh bằng chứng liên quan sẽ bị xóa vĩnh viễn khỏi hệ thống.",
        kind="warning",
        title="Cảnh báo xóa dữ liệu ca thi"
    )
    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Hủy bỏ", use_container_width=True):
            st.rerun()
    with c2:
        if st.button("Xác nhận xóa", type="primary", use_container_width=True):
            handle_delete(session_id)


# ── Xử lý query params ─────────────────────────────────────
if "confirm_delete" in st.query_params:
    try:
        target_sid = int(st.query_params["confirm_delete"])
        del st.query_params["confirm_delete"]
        confirm_delete_dialog(target_sid)
    except Exception:
        pass

if "view_ev" in st.query_params:
    try:
        v_ev_id = int(st.query_params["view_ev"])
        show_evidence_dialog(v_ev_id)
    except Exception:
        pass

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
            notify.success(f"Đã bác bỏ sự kiện EV-{r_ev_id:02d} (Giấy thi hợp lệ)")
            st.rerun()
        else:
            notify.error("Không thể cập nhật trạng thái sự kiện")
    except Exception:
        pass

if "select_session" in st.query_params:
    try:
        target_sel_sid = int(st.query_params["select_session"])
        del st.query_params["select_session"]
        st.session_state["history_selected_sid"] = target_sel_sid
        st.session_state["history_active_tab"] = "events"
    except Exception:
        pass

if "tab" in st.query_params:
    if st.query_params["tab"] == "events":
        st.session_state["history_active_tab"] = "events"
    elif st.query_params["tab"] == "sessions":
        st.session_state["history_active_tab"] = "sessions"

# ── Điều hướng Tab con ──────────────────────────────────────
tab_sessions, tab_events = st.tabs(["Danh mục ca thi", "Nhật ký sự kiện"])


# =========================================================================
# TAB 1: DANH MỤC CA THI
# =========================================================================
with tab_sessions:
    # Phân trang & Tìm kiếm ca thi
    if "hist_page" not in st.session_state:
        st.session_state.hist_page = 1
    if "hist_search" not in st.session_state:
        st.session_state.hist_search = ""

    if "p" in st.query_params:
        try:
            st.session_state.hist_page = max(1, int(st.query_params["p"]))
        except Exception:
            pass

    # 1. Summary Cards
    def _fetch_history(session, search: str = "", page: int = 1) -> dict:
        skip = (page - 1) * PAGE_SIZE
        sessions = get_history(session, search=search, skip=skip, limit=PAGE_SIZE)
        try:
            summary = get_history_summary(session, search=search)
        except Exception:
            summary = {}
        return {
            "sessions": sessions or [],
            "total_sessions": summary.get("tong_phien", 0) if summary else 0,
            "total_events": summary.get("tong_su_kien", 0) if summary else 0,
        }

    data = _fetch_history(client, search=st.session_state.hist_search, page=st.session_state.hist_page)
    sessions = data["sessions"]
    total_sessions_count = data["total_sessions"]
    total_pages = max((total_sessions_count - 1) // PAGE_SIZE + 1, 1)

    if st.session_state.hist_page > total_pages:
        st.session_state.hist_page = total_pages
    current_page = st.session_state.hist_page

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        st.markdown(f"""
        <div class="summary-card">
            <div class="label">TỔNG PHIÊN GIÁM SÁT</div>
            <div class="value">{data['total_sessions']:,}</div>
            <div class="trend up">Toàn bộ ca thi trong cơ sở dữ liệu</div>
        </div>
        """, unsafe_allow_html=True)

    with col_s2:
        st.markdown(f"""
        <div class="summary-card">
            <div class="label">TỔNG SỰ KIỆN GIAN LẬN</div>
            <div class="value">{data['total_events']:,}</div>
            <div class="trend neutral">Đã ghi nhận trong cơ sở dữ liệu</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height: 6px;'></div>", unsafe_allow_html=True)

    # 2. Ô tìm kiếm
    search_val = st.text_input(
        "Tìm kiếm theo phòng hoặc môn thi",
        value=st.session_state.hist_search,
        placeholder="Nhập tên phòng hoặc môn thi để lọc danh mục...",
        label_visibility="collapsed",
    )
    if search_val != st.session_state.hist_search:
        st.session_state.hist_search = search_val
        st.session_state.hist_page = 1
        st.rerun()

    # 3. Bảng danh mục ca thi
    if not sessions:
        notify.empty_state("Không tìm thấy ca thi nào phù hợp", "Vui lòng thử tìm kiếm với từ khóa khác để hiển thị toàn bộ ca thi.")
    else:
        # Tiêu đề hàng bảng ca thi
        sh1, sh2, sh3, sh4, sh5 = st.columns([1, 2, 2, 1.2, 1.4])
        sh1.caption("MÃ CA")
        sh2.caption("PHÒNG / MÔN THI")
        sh3.caption("THỜI GIAN")
        sh4.caption("TRẠNG THÁI")
        sh5.markdown('<div style="text-align:right; font-size:11.5px; font-weight:700; color:#64748b; letter-spacing:0.5px;">THAO TÁC</div>', unsafe_allow_html=True)

        st.markdown("<hr style='margin: 4px 0 8px 0; border: none; border-top: 1px solid var(--wf-border);'>", unsafe_allow_html=True)

        for s in sessions:
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
                        f'  <a href="/history?tab=events&select_session={s_id}" class="action-svg-btn event-btn" title="Xem các sự kiện gian lận của ca thi này">'
                        f'    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
                        f'      <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>'
                        f'      <path d="M13.73 21a2 2 0 0 1-3.46 0"/>'
                        f'    </svg>'
                        f'  </a>'
                        f'  <a href="/history?confirm_delete={s_id}" class="action-svg-btn del-btn" title="Xóa ca thi này khỏi hệ thống">'
                        f'    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
                        f'      <polyline points="3 6 5 6 21 6"/>'
                        f'      <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>'
                        f'      <line x1="10" y1="11" x2="10" y2="17"/>'
                        f'      <line x1="14" y1="11" x2="14" y2="17"/>'
                        f'    </svg>'
                        f'  </a>'
                        f'</div>'
                    )
                    st.markdown(action_sess_html, unsafe_allow_html=True)

            st.markdown("<hr style='margin: 4px 0 10px 0; border: none; border-top: 1px solid var(--wf-border);'>", unsafe_allow_html=True)

        # 4. Phân trang nhỏ gọn Figma Standard
        start_idx = (current_page - 1) * PAGE_SIZE + 1 if total_sessions_count > 0 else 0
        end_idx = min(current_page * PAGE_SIZE, total_sessions_count)

        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
        pg_left, pg_spacer, pg_right = st.columns([5, 2, 5])
        with pg_left:
            st.markdown(
                f"<div style='font-size: 13px; color: #64748b; line-height: 32px;'>"
                f"Hiển thị <strong>{start_idx} – {end_idx}</strong> trong tổng số <strong>{total_sessions_count}</strong> ca thi"
                f"</div>",
                unsafe_allow_html=True,
            )

        with pg_right:
            pag_items = []
            prev_disabled = "opacity: 0.35; pointer-events: none;" if current_page <= 1 else ""
            pag_items.append(f'<a href="/history?p={current_page - 1}" style="{prev_disabled}">‹</a>')

            for p in range(1, total_pages + 1):
                if total_pages > 7 and abs(p - current_page) > 2 and p != 1 and p != total_pages:
                    if p == 2 or p == total_pages - 1:
                        pag_items.append('<span style="color: #94a3b8; line-height: 32px; padding: 0 4px;">…</span>')
                    continue
                active_cls = "active" if p == current_page else ""
                pag_items.append(f'<a href="/history?p={p}" class="{active_cls}">{p}</a>')

            next_disabled = "opacity: 0.35; pointer-events: none;" if current_page >= total_pages else ""
            pag_items.append(f'<a href="/history?p={current_page + 1}" style="{next_disabled}">›</a>')

            st.markdown(f'<div class="history-pagination">{"".join(pag_items)}</div>', unsafe_allow_html=True)


# =========================================================================
# TAB 2: NHẬT KÝ SỰ KIỆN GIAN LẬN
# =========================================================================
with tab_events:
    all_sessions_list = get_all_sessions(client)

    # 1. Bộ lọc 3 cột
    f_c1, f_c2, f_c3 = st.columns([1.6, 1.2, 1.2])

    with f_c1:
        # Tùy chọn 0: Tất cả phiên giám sát (Yêu cầu đặc biệt của người dùng)
        session_options = {0: "Tất cả phiên giám sát"}
        for s in all_sessions_list:
            sid_item = s["PK_MaPhienGiamSat"]
            room_item = s.get("PhongThi") or "P.Thi"
            sub_item = s.get("MonThi") or "Môn"
            session_options[sid_item] = f"Phiên #{sid_item} - {room_item} ({sub_item})"

        # Ưu tiên session được chọn từ URL hoặc session_state
        def_sid = st.session_state.get("history_selected_sid")
        if def_sid is None or def_sid not in session_options:
            def_sid = 0

        keys_list = list(session_options.keys())
        def_idx = keys_list.index(def_sid) if def_sid in keys_list else 0

        selected_sid = st.selectbox(
            "Chọn phiên giám sát:",
            options=keys_list,
            index=def_idx,
            format_func=lambda x: session_options.get(x, f"Phiên #{x}"),
            key="hist_events_sel_session",
        )
        st.session_state["history_selected_sid"] = selected_sid

    with f_c2:
        filter_behavior = st.selectbox(
            "Loại hành vi",
            ["Tất cả", "Tài liệu giấy (Cheat_Paper)", "Điện thoại di động (cellphone)", "Quay đầu trao đổi (Head_Turn)"],
            key="hist_events_filter_bh",
        )

    with f_c3:
        filter_status_vn = st.selectbox(
            "Trạng thái kiểm tra",
            ["Tất cả", "Chờ kiểm tra", "Đã xác nhận", "Bác bỏ"],
            key="hist_events_filter_stt",
        )
        status_map = {"Tất cả": "", "Chờ kiểm tra": "cho_kiem_tra", "Đã xác nhận": "dung", "Bác bỏ": "sai"}
        filter_status = status_map.get(filter_status_vn, "")

    # 2. Lấy dữ liệu sự kiện
    if selected_sid == 0:
        events = list_all_events(client, trang_thai=filter_status, limit=200)
        # Fallback an toàn: nếu endpoint trả về rỗng, lấy gộp từ từng session
        if not events and all_sessions_list:
            pool = []
            for s in all_sessions_list:
                s_evs = list_session_events(client, s["PK_MaPhienGiamSat"], trang_thai=filter_status, limit=50)
                if s_evs:
                    pool.extend(s_evs)
            events = pool
        session_title = "Tất cả các ca thi trong cơ sở dữ liệu"
    else:
        events = list_session_events(client, selected_sid, trang_thai=filter_status, limit=100)
        session_title = f"Phiên #{selected_sid}"

    # Lọc hành vi phía client
    if filter_behavior != "Tất cả":
        key_check = "Cheat_Paper" if "Cheat_Paper" in filter_behavior else ("cellphone" if "cellphone" in filter_behavior else "Head_Turn")
        events = [e for e in events if key_check.lower() in (e.get("LoaiHanhVi") or "").lower()]

    st.markdown(f"""
    <div class="wf-box">
        <div class="wf-box-header">
            <div class="wf-box-title">Danh sách sự kiện phát hiện gian lận · {session_title}</div>
            <div>
                <span class="wf-badge danger">Tổng sự kiện: {len(events)}</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if not events:
        notify.empty_state("Không có sự kiện vi phạm nào", "Không tìm thấy sự kiện nào khớp với tiêu chí lọc hoặc phiên thi này chưa ghi nhận vi phạm gian lận.")
    else:
        # Header hàng bảng
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
                        f'  <a href="/history?tab=events&view_ev={ev_id}" class="action-svg-btn view-btn" title="Xem nhanh bằng chứng & xác minh vi phạm">'
                        f'    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
                        f'      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8z"/>'
                        f'      <circle cx="12" cy="12" r="3"/>'
                        f'    </svg>'
                        f'  </a>'
                        f'  <a href="/history?tab=events&confirm_ev={ev_id}&raw_label={raw_label}" class="action-svg-btn confirm-btn" title="Xác nhận đúng vi phạm ({friendly_label})">'
                        f'    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
                        f'      <polyline points="20 6 9 17 4 12"/>'
                        f'    </svg>'
                        f'  </a>'
                        f'  <a href="/history?tab=events&reject_ev={ev_id}" class="action-svg-btn reject-btn" title="Bác bỏ vi phạm (Báo sai: Giấy thi hợp lệ)">'
                        f'    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
                        f'      <line x1="18" y1="6" x2="6" y2="18"/>'
                        f'      <line x1="6" y1="6" x2="18" y2="18"/>'
                        f'    </svg>'
                        f'  </a>'
                        f'</div>'
                    )
                    st.markdown(action_html, unsafe_allow_html=True)

            st.markdown("<hr style='margin: 4px 0 8px 0; border: none; border-top: 1px solid var(--wf-border);'>", unsafe_allow_html=True)
