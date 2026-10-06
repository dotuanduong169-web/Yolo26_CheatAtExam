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
from utils.http import auth_query_params, init_session_state
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
# Chuỗi giữ phiên cho link HTML (tránh reload mất đăng nhập)
aqs = auth_query_params()

# ── Dialogs & Thao tác nghiệp vụ ───────────────────────────
def handle_delete(session_id: int) -> None:
    """Xóa phiên và hiện kết quả."""
    res = delete_session(client, session_id)
    if not res:
        notify.inline_error("Không thể kết nối đến máy chủ.")
        return
    if res.status_code == 200:
        notify.defer_success(f"Đã xóa phiên giám sát #{session_id} thành công.")
        st.rerun()
    elif res.status_code == 400:
        notify.inline_error("Không thể xóa phiên đang diễn ra.")
    elif res.status_code == 404:
        notify.inline_error("Không tìm thấy phiên giám sát.")
    else:
        notify.inline_error(f"Lỗi hệ thống: {res.text}")


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


# ── Nhận diện tương tác bộ lọc sự kiện để duy trì tab Nhật ký sự kiện ──
curr_ev_bh = st.session_state.get("hist_events_filter_bh")
curr_ev_stt = st.session_state.get("hist_events_filter_stt")
curr_ev_sid = st.session_state.get("hist_events_sel_session")

last_ev_bh = st.session_state.get("_last_hist_events_filter_bh")
last_ev_stt = st.session_state.get("_last_hist_events_filter_stt")
last_ev_sid = st.session_state.get("_last_hist_events_sel_session")

if (
    (curr_ev_bh != last_ev_bh and last_ev_bh is not None)
    or (curr_ev_stt != last_ev_stt and last_ev_stt is not None)
    or (curr_ev_sid != last_ev_sid and last_ev_sid is not None)
):
    st.session_state["history_active_tab"] = "events"

st.session_state["_last_hist_events_filter_bh"] = curr_ev_bh
st.session_state["_last_hist_events_filter_stt"] = curr_ev_stt
st.session_state["_last_hist_events_sel_session"] = curr_ev_sid

# ── Xử lý query params từ link icon SVG (giữ phiên qua auth params trong URL) ──
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
        del st.query_params["view_ev"]
        st.session_state["history_active_tab"] = "events"
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
        st.session_state["history_active_tab"] = "events"
        res = verify_event(client, c_ev_id, "dung", c_raw_label)
        if res is not None and res.status_code == 200:
            notify.defer_success(f"Đã xác nhận sự kiện EV-{c_ev_id:02d} là Vi phạm")
            st.rerun()
        else:
            notify.error("Không thể cập nhật trạng thái sự kiện")
    except Exception:
        pass

if "reject_ev" in st.query_params:
    try:
        r_ev_id = int(st.query_params["reject_ev"])
        del st.query_params["reject_ev"]
        st.session_state["history_active_tab"] = "events"
        res = verify_event(client, r_ev_id, "sai", "Answer_paper")
        if res is not None and res.status_code == 200:
            notify.defer_success(f"Đã bác bỏ sự kiện EV-{r_ev_id:02d} (Giấy thi hợp lệ)")
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
    try:
        del st.query_params["tab"]
    except Exception:
        pass

# ── Cố định vị trí Tab con theo chuẩn: [Danh mục ca thi, Nhật ký sự kiện] ──
tab_sessions, tab_events = st.tabs(["Danh mục ca thi", "Nhật ký sự kiện"])

current_forced_tab = st.session_state.get("history_active_tab") or ""

st.components.v1.html(
    f"""
    <script>
    (function() {{
        function initTabSync() {{
            try {{
                const tabs = window.parent.document.querySelectorAll('div[data-testid="stTabs"] button[role="tab"]');
                if (!tabs || tabs.length < 2) return;

                if (!tabs[0].dataset.syncBound) {{
                    tabs[0].dataset.syncBound = "true";
                    tabs[0].addEventListener('click', function() {{
                        try {{ window.parent.sessionStorage.setItem('history_active_tab_idx', '0'); }} catch(e){{}}
                    }});
                }}
                if (!tabs[1].dataset.syncBound) {{
                    tabs[1].dataset.syncBound = "true";
                    tabs[1].addEventListener('click', function() {{
                        try {{ window.parent.sessionStorage.setItem('history_active_tab_idx', '1'); }} catch(e){{}}
                    }});
                }}

                const forced = "{current_forced_tab}";
                let targetIdx = null;

                if (forced === "events") {{
                    targetIdx = 1;
                    try {{ window.parent.sessionStorage.setItem('history_active_tab_idx', '1'); }} catch(e){{}}
                }} else if (forced === "sessions") {{
                    targetIdx = 0;
                    try {{ window.parent.sessionStorage.setItem('history_active_tab_idx', '0'); }} catch(e){{}}
                }} else {{
                    try {{
                        const saved = window.parent.sessionStorage.getItem('history_active_tab_idx');
                        if (saved === '1') targetIdx = 1;
                        else if (saved === '0') targetIdx = 0;
                    }} catch(e){{}}
                }}

                if (targetIdx !== null && targetIdx < tabs.length) {{
                    const isSelected = tabs[targetIdx].getAttribute('aria-selected') === 'true';
                    if (!isSelected) {{
                        tabs[targetIdx].click();
                    }}
                }}
            }} catch(e) {{}}
        }}

        initTabSync();
        setTimeout(initTabSync, 50);
        setTimeout(initTabSync, 150);
        setTimeout(initTabSync, 300);
    }})();
    </script>
    """,
    height=0,
    width=0,
)


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
        st.session_state["history_active_tab"] = "sessions"
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
                    act_c1, act_c2 = st.columns([1, 1])
                    with act_c1:
                        if st.button(" ", key=f"btn_act_view_sess_{s_id}", help=f"Xem báo cáo chi tiết ca thi #{s_id}"):
                            st.session_state["selected_session"] = s_id
                            st.session_state["session_id"] = s_id
                            st.switch_page("pages/session_detail.py")
                    with act_c2:
                        if st.button(" ", key=f"btn_act_del_sess_{s_id}", help="Xóa ca thi này khỏi hệ thống"):
                            confirm_delete_dialog(s_id)

            st.markdown("<hr style='margin: 4px 0 10px 0; border: none; border-top: 1px solid var(--wf-border);'>", unsafe_allow_html=True)

        # 4. Phân trang nhỏ gọn Figma Standard
        start_idx = (current_page - 1) * PAGE_SIZE + 1 if total_sessions_count > 0 else 0
        end_idx = min(current_page * PAGE_SIZE, total_sessions_count)

        st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)
        pg_left, pg_right = st.columns([1, 1])
        with pg_left:
            st.markdown(
                f"<div style='font-size: 13px; color: #64748b; line-height: 32px; font-weight: 500;'>"
                f"Hiển thị <strong>{start_idx} – {end_idx}</strong> trong tổng số <strong>{total_sessions_count}</strong> ca thi"
                f"</div>",
                unsafe_allow_html=True,
            )

        with pg_right:
            p_items = []
            p_items.append(("‹", max(1, current_page - 1), current_page <= 1))
            for p in range(1, total_pages + 1):
                if total_pages > 7 and abs(p - current_page) > 2 and p != 1 and p != total_pages:
                    continue
                p_items.append((str(p), p, False))
            p_items.append(("›", min(total_pages, current_page + 1), current_page >= total_pages))

            n_btn = len(p_items)
            p_cols = st.columns([1] * (7 - n_btn) + [1] * n_btn if n_btn < 7 else [1] * n_btn)
            offset = 7 - n_btn if n_btn < 7 else 0

            for i, (lbl, target_p, is_dis) in enumerate(p_items):
                with p_cols[offset + i]:
                    is_cur = (lbl == str(current_page))
                    btn_t = "primary" if is_cur else "secondary"
                    if st.button(lbl, key=f"pag_btn_sess_{lbl}_{target_p}", disabled=is_dis, type=btn_t, use_container_width=True):
                        if target_p != current_page:
                            st.session_state.hist_page = target_p
                            st.session_state["history_active_tab"] = "sessions"
                            st.rerun()



# =========================================================================
# TAB 2: NHẬT KÝ SỰ KIỆN GIAN LẬN
# =========================================================================
with tab_events:
    # Luôn xóa query param view_ev nếu còn sót lại để không mở lại dialog cũ khi chọn bộ lọc
    if "view_ev" in st.query_params:
        try:
            del st.query_params["view_ev"]
        except Exception:
            pass

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
                    ev_c1, ev_c2, ev_c3 = st.columns([1, 1, 1])
                    with ev_c1:
                        if st.button(" ", key=f"btn_act_view_ev_{ev_id}", help="Xem nhanh bằng chứng vi phạm"):
                            st.session_state["history_active_tab"] = "events"
                            show_evidence_dialog(ev_id)
                    with ev_c2:
                        if st.button(" ", key=f"btn_act_confirm_ev_{ev_id}", help=f"Xác nhận đúng vi phạm ({friendly_label})"):
                            st.session_state["history_active_tab"] = "events"
                            res = verify_event(client, ev_id, "dung", raw_label)
                            if res is not None and res.status_code == 200:
                                notify.defer_success(f"Đã xác nhận sự kiện EV-{ev_id:02d} ({friendly_label})")
                            else:
                                notify.error("Không thể xác nhận sự kiện")
                            st.rerun()
                    with ev_c3:
                        if st.button(" ", key=f"btn_act_reject_ev_{ev_id}", help="Bác bỏ vi phạm (Giấy thi hợp lệ)"):
                            st.session_state["history_active_tab"] = "events"
                            res = verify_event(client, ev_id, "sai", "Answer_paper")
                            if res is not None and res.status_code == 200:
                                notify.defer_success(f"Đã bác bỏ sự kiện EV-{ev_id:02d}")
                            else:
                                notify.error("Không thể bác bỏ sự kiện")
                            st.rerun()

            st.markdown("<hr style='margin: 4px 0 8px 0; border: none; border-top: 1px solid var(--wf-border);'>", unsafe_allow_html=True)
