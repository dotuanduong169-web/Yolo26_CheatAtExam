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
        st.query_params["tab"] = "events"

        # Chỉ mở dialog nếu chưa hiển thị sự kiện này trong lượt hiện tại
        if st.session_state.get("last_handled_view_ev") != v_ev_id:
            st.session_state["last_handled_view_ev"] = v_ev_id
            # Dọn sạch query param view_ev trên URL thanh địa chỉ trình duyệt để tránh lọc/rerun mở lại modal
            st.components.v1.html(
                """
                <script>
                (function() {
                    try {
                        const p = window.parent || window;
                        const u = new URL(p.location.href);
                        if (u.searchParams.has('view_ev')) {
                            u.searchParams.delete('view_ev');
                            p.history.replaceState({}, '', u.pathname + u.search);
                        }
                    } catch(e) {}
                })();
                </script>
                """,
                height=0,
                width=0,
            )
            show_evidence_dialog(v_ev_id)
    except Exception:
        pass
else:
    # Khi URL không còn view_ev, reset flag để lần click tiếp theo vẫn mở bình thường
    st.session_state["last_handled_view_ev"] = None

if "confirm_ev" in st.query_params:
    try:
        c_ev_id = int(st.query_params["confirm_ev"])
        c_raw_label = st.query_params.get("raw_label", "")
        del st.query_params["confirm_ev"]
        if "raw_label" in st.query_params:
            del st.query_params["raw_label"]
        st.session_state["history_active_tab"] = "events"
        st.query_params["tab"] = "events"
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
        st.query_params["tab"] = "events"
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
        st.query_params["tab"] = "events"
    except Exception:
        pass

# ── Quản lý Tab con chuẩn hệ thống: [Danh mục ca thi, Nhật ký sự kiện] ──
tab_sessions, tab_events = st.tabs(["Danh mục ca thi", "Nhật ký sự kiện"])

target_tab_idx = 1 if st.session_state.get("history_active_tab") == "events" or st.query_params.get("tab") == "events" else 0

st.components.v1.html(
    f"""
    <script>
    (function() {{
        function syncTabs() {{
            try {{
                const tabs = window.parent.document.querySelectorAll('div[data-testid="stTabs"] button[role="tab"]');
                if (!tabs || tabs.length < 2) return;

                if (!tabs[0].dataset.syncListener) {{
                    tabs[0].dataset.syncListener = "1";
                    tabs[0].addEventListener('click', function() {{
                        try {{
                            window.parent.sessionStorage.setItem('hist_subtab_idx', '0');
                            const u = new URL(window.parent.location.href);
                            u.searchParams.set('tab', 'sessions');
                            window.parent.history.replaceState({{}}, '', u.pathname + u.search);
                        }} catch(e) {{}}
                    }});
                }}
                if (!tabs[1].dataset.syncListener) {{
                    tabs[1].dataset.syncListener = "1";
                    tabs[1].addEventListener('click', function() {{
                        try {{
                            window.parent.sessionStorage.setItem('hist_subtab_idx', '1');
                            const u = new URL(window.parent.location.href);
                            u.searchParams.set('tab', 'events');
                            window.parent.history.replaceState({{}}, '', u.pathname + u.search);
                        }} catch(e) {{}}
                    }});
                }}

                const url = new URL(window.parent.location.href);
                const qTab = url.searchParams.get('tab');
                const savedIdx = window.parent.sessionStorage.getItem('hist_subtab_idx');

                let shouldBe1 = false;
                if (qTab === 'events' || {str(target_tab_idx == 1).lower()}) {{
                    shouldBe1 = true;
                }} else if (qTab === 'sessions') {{
                    shouldBe1 = false;
                }} else if (savedIdx === '1') {{
                    shouldBe1 = true;
                }}

                if (shouldBe1 && tabs[1].getAttribute('aria-selected') !== 'true') {{
                    tabs[1].click();
                }} else if (!shouldBe1 && tabs[0].getAttribute('aria-selected') !== 'true' && savedIdx === '0') {{
                    tabs[0].click();
                }}
            }} catch(e) {{}}
        }}

        syncTabs();
        setTimeout(syncTabs, 40);
        setTimeout(syncTabs, 120);
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
            del st.query_params["p"]
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

    # 2. Ô tìm kiếm (callback chạy trước body nên fetch ở trên đã thấy
    # giá trị mới trong cùng 1 rerun — không rerun thủ công lần 2)
    def _on_hist_search_change() -> None:
        st.session_state.hist_search = st.session_state.get("hist_search_input", "")
        st.session_state.hist_page = 1

    if "hist_search_input" not in st.session_state:
        st.session_state.hist_search_input = st.session_state.hist_search
    st.text_input(
        "Tìm kiếm theo phòng hoặc môn thi",
        placeholder="Nhập tên phòng hoặc môn thi để lọc danh mục...",
        label_visibility="collapsed",
        key="hist_search_input",
        on_change=_on_hist_search_change,
    )

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
                    # Nút native (icon vẽ bằng CSS btn_act_*) → rerun nhẹ,
                    # không reload trình duyệt nên không chớp (giao diện giữ nguyên)
                    ab1, ab2 = st.columns([1, 1], gap="small")
                    with ab1:
                        if st.button("Xem", key=f"btn_act_view_sess_{s_id}", help=f"Xem báo cáo chi tiết ca thi #{s_id}"):
                            st.session_state["selected_session"] = s_id
                            st.session_state["session_id"] = s_id
                            st.switch_page("pages/session_detail.py")
                    with ab2:
                        if st.button("Xóa", key=f"btn_act_del_sess_{s_id}", help="Xóa ca thi này khỏi hệ thống"):
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
            # Phân trang native (key pag_btn_sess_*, CSS Figma sẵn) — rerun nhẹ
            _pages: list = []
            for p in range(1, total_pages + 1):
                if total_pages > 7 and abs(p - current_page) > 2 and p != 1 and p != total_pages:
                    if p == 2 or p == total_pages - 1:
                        _pages.append(None)
                    continue
                _pages.append(p)
            _cols = st.columns(len(_pages) + 2, gap="small")
            with _cols[0]:
                if st.button("‹", key="pag_btn_sess_prev", disabled=(current_page <= 1)):
                    st.session_state.hist_page = current_page - 1
                    st.rerun()
            for _i, _p in enumerate(_pages):
                with _cols[_i + 1]:
                    if _p is None:
                        st.markdown("<div style='display:flex;align-items:center;justify-content:center;height:32px;color:#94a3b8;'>…</div>", unsafe_allow_html=True)
                    elif _p == current_page:
                        st.button(str(_p), key=f"pag_btn_sess_cur_{_p}", type="primary", disabled=True)
                    elif st.button(str(_p), key=f"pag_btn_sess_{_p}"):
                        st.session_state.hist_page = _p
                        st.rerun()
            with _cols[-1]:
                if st.button("›", key="pag_btn_sess_next", disabled=(current_page >= total_pages)):
                    st.session_state.hist_page = current_page + 1
                    st.rerun()


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
        # 3. Phân trang cho nhật ký sự kiện
        EV_PAGE_SIZE = 10
        total_ev_count = len(events)
        total_ev_pages = max(1, (total_ev_count - 1) // EV_PAGE_SIZE + 1)

        if "hist_ev_page" not in st.session_state:
            st.session_state.hist_ev_page = 1
        cur_ev_p = st.session_state.hist_ev_page
        if "p_ev" in st.query_params:
            try:
                cur_ev_p = max(1, int(st.query_params["p_ev"]))
                st.session_state.hist_ev_page = cur_ev_p
                del st.query_params["p_ev"]
            except Exception:
                pass
        if cur_ev_p > total_ev_pages:
            cur_ev_p = total_ev_pages
            st.session_state.hist_ev_page = cur_ev_p

        ev_start_idx = (cur_ev_p - 1) * EV_PAGE_SIZE
        ev_end_idx = min(ev_start_idx + EV_PAGE_SIZE, total_ev_count)
        page_events = events[ev_start_idx:ev_end_idx]

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

        for ev in page_events:
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
                    # Nút native (icon CSS btn_act_*) → dialog/API trực tiếp, không qua URL
                    eb1, eb2, eb3 = st.columns(3, gap="small")
                    with eb1:
                        if st.button("Xem", key=f"btn_act_view_ev_{ev_id}", help="Xem nhanh bằng chứng vi phạm"):
                            show_evidence_dialog(ev_id)
                    with eb2:
                        if st.button("Duyệt", key=f"btn_act_confirm_ev_{ev_id}", help=f"Xác nhận đúng vi phạm ({friendly_label})"):
                            st.session_state["history_active_tab"] = "events"
                            res = verify_event(client, ev_id, "dung", raw_label)
                            if res is not None and res.status_code == 200:
                                notify.defer_success(f"Đã xác nhận sự kiện EV-{ev_id:02d} là Vi phạm")
                                st.rerun()
                            else:
                                notify.error("Không thể cập nhật trạng thái sự kiện")
                    with eb3:
                        if st.button("Bỏ", key=f"btn_act_reject_ev_{ev_id}", help="Bác bỏ vi phạm (Giấy thi hợp lệ)"):
                            st.session_state["history_active_tab"] = "events"
                            res = verify_event(client, ev_id, "sai", "Answer_paper")
                            if res is not None and res.status_code == 200:
                                notify.defer_success(f"Đã bác bỏ sự kiện EV-{ev_id:02d} (Giấy thi hợp lệ)")
                                st.rerun()
                            else:
                                notify.error("Không thể cập nhật trạng thái sự kiện")

            st.markdown("<hr style='margin: 4px 0 8px 0; border: none; border-top: 1px solid var(--wf-border);'>", unsafe_allow_html=True)

        # Cụm phân trang cho nhật ký sự kiện chuẩn Figma
        st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)
        ev_pg_left, ev_pg_right = st.columns([1, 1])
        with ev_pg_left:
            st.markdown(
                f"<div style='font-size: 13px; color: #64748b; line-height: 32px; font-weight: 500;'>"
                f"Hiển thị <strong>{ev_start_idx + 1} – {ev_end_idx}</strong> trong tổng số <strong>{total_ev_count}</strong> sự kiện"
                f"</div>",
                unsafe_allow_html=True,
            )

        with ev_pg_right:
            # Phân trang native — rerun nhẹ, không reload trình duyệt
            _ev_pages: list = []
            for p in range(1, total_ev_pages + 1):
                if total_ev_pages > 7 and abs(p - cur_ev_p) > 2 and p != 1 and p != total_ev_pages:
                    if p == 2 or p == total_ev_pages - 1:
                        _ev_pages.append(None)
                    continue
                _ev_pages.append(p)
            _ecols = st.columns(len(_ev_pages) + 2, gap="small")
            with _ecols[0]:
                if st.button("‹", key="pag_btn_ev_prev", disabled=(cur_ev_p <= 1)):
                    st.session_state.hist_ev_page = cur_ev_p - 1
                    st.rerun()
            for _i, _p in enumerate(_ev_pages):
                with _ecols[_i + 1]:
                    if _p is None:
                        st.markdown("<div style='display:flex;align-items:center;justify-content:center;height:32px;color:#94a3b8;'>…</div>", unsafe_allow_html=True)
                    elif _p == cur_ev_p:
                        st.button(str(_p), key=f"pag_btn_ev_cur_{_p}", type="primary", disabled=True)
                    elif st.button(str(_p), key=f"pag_btn_ev_{_p}"):
                        st.session_state.hist_ev_page = _p
                        st.rerun()
            with _ecols[-1]:
                if st.button("›", key="pag_btn_ev_next", disabled=(cur_ev_p >= total_ev_pages)):
                    st.session_state.hist_ev_page = cur_ev_p + 1
                    st.rerun()
