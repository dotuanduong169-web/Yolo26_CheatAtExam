import base64
import html
import io

import streamlit as st
from utils.notify import notify
from PIL import Image

from config import API_BASE_URL
from services.event_api import (
    get_event_detail,
    get_evidence_bytes,
    list_session_events,
    verify_event,
)
from utils.auth_guard import require_auth
from utils.hide_streamlit_sidebar import hide_sidebar
from utils.http import auth_query_params, init_session_state
from utils.load_css import load_css
from utils.render_header import render_page_header
from utils.status_helpers import get_event_status_info, get_friendly_behavior_label

# ── Config ──────────────────────────────────────────────────
st.set_page_config(layout="wide", initial_sidebar_state="collapsed", page_title="Chi tiết sự kiện")

init_session_state()
require_auth()

# ── Sidebar & Styles ───────────────────────────────────────
hide_sidebar()
st.markdown(load_css("styles/sidebar.css"), unsafe_allow_html=True)
st.markdown(load_css("styles/app_theme.css"), unsafe_allow_html=True)
st.markdown(load_css("styles/event_detail.css"), unsafe_allow_html=True)

# ── Event ID & Session ID ───────────────────────────────────
target_eid = st.query_params.get("id") or st.query_params.get("event_id")
if target_eid:
    try:
        st.session_state["event_id"] = int(target_eid)
    except Exception:
        pass

if "from_session" in st.query_params:
    try:
        st.session_state["from_session_id"] = int(st.query_params["from_session"])
        st.session_state["selected_session"] = int(st.query_params["from_session"])
        st.session_state["session_id"] = int(st.query_params["from_session"])
    except Exception:
        pass

event_id = st.session_state.get("event_id")
from_sess_id = (
    st.query_params.get("from_session")
    or st.session_state.get("from_session_id")
    or st.session_state.get("selected_session")
    or st.session_state.get("session_id")
)
try:
    if from_sess_id is not None:
        from_sess_id = int(from_sess_id)
        st.session_state["from_session_id"] = from_sess_id
        st.session_state["selected_session"] = from_sess_id
        st.session_state["session_id"] = from_sess_id
except Exception:
    pass

if not event_id:
    render_page_header("Chi tiết sự kiện", active="history")
    if from_sess_id:
        if st.button("← Quay lại chi tiết ca thi", key="btn_back_sess_noid"):
            st.session_state["selected_session"] = from_sess_id
            st.session_state["session_id"] = from_sess_id
            st.switch_page("pages/session_detail.py")
    else:
        if st.button("← Quay lại danh sách lịch sử", key="btn_back_hist_noid"):
            st.switch_page("pages/history.py")
    notify.inline("Không tìm thấy mã sự kiện cần xem. Vui lòng quay lại danh sách sự kiện.", kind="warning", title="Thiếu mã sự kiện")
    st.stop()


# ── Load Data ───────────────────────────────────────────────
data = get_event_detail(st.session_state.client, event_id)
if not data:
    render_page_header(f"Chi tiết sự kiện #EV-{event_id:02d}", active="history")
    if from_sess_id:
        cb_col1, cb_col2, _ = st.columns([1.5, 1.5, 3])
        with cb_col1:
            if st.button("← Quay lại chi tiết ca thi", key="btn_back_sess_nodata"):
                st.session_state["selected_session"] = from_sess_id
                st.session_state["session_id"] = from_sess_id
                st.switch_page("pages/session_detail.py")
        with cb_col2:
            if st.button("Quay lại danh mục ca thi", key="btn_back_hist_nodata"):
                st.session_state["history_active_tab"] = "sessions"
                st.switch_page("pages/history.py")
    else:
        if st.button("← Quay lại danh mục ca thi", key="btn_back_hist_nodata"):
            st.session_state["history_active_tab"] = "sessions"
            st.switch_page("pages/history.py")

    notify.inline("Không lấy được dữ liệu chi tiết sự kiện từ máy chủ. Sự kiện có thể không tồn tại hoặc đã bị xóa.", kind="error", title="Lỗi tải dữ liệu")
    st.stop()

# Cập nhật from_sess_id từ data nếu trước đó chưa có
if not from_sess_id and data.get("FK_MaPhienGiamSat"):
    try:
        from_sess_id = int(data["FK_MaPhienGiamSat"])
        st.session_state["from_session_id"] = from_sess_id
        st.session_state["selected_session"] = from_sess_id
        st.session_state["session_id"] = from_sess_id
    except Exception:
        pass

raw_label = data.get("LoaiHanhVi", "?")
conf = round(float(data.get("DoTinCay", 0)) * 100, 1)
trang_thai = data.get("TrangThaiKiemTra", "cho_kiem_tra")
bbox = data.get("ToaDo") or []
evidences = data.get("evidences", [])
cam_role = data.get("VaiTroCamera") or (
    evidences[0].get("VaiTroCamera") if evidences else None
) or "front"
cam_label = "Camera phụ (điện thoại)" if cam_role == "side" else "Camera trước (webcam)"

friendly_label = get_friendly_behavior_label(raw_label)
stt_text, stt_cls = get_event_status_info(trang_thai)

# ── Header ──────────────────────────────────────────────────
render_page_header(f"Chi tiết sự kiện #EV-{event_id:02d}", active="history")

if from_sess_id:
    c_back1, c_back2, _ = st.columns([0.22, 0.22, 0.56], gap="small")
    with c_back1:
        if st.button("← Quay lại chi tiết ca thi", key="btn_back_session"):
            st.session_state["selected_session"] = from_sess_id
            st.session_state["session_id"] = from_sess_id
            st.query_params["id"] = str(from_sess_id)
            if "from_session" in st.query_params:
                del st.query_params["from_session"]
            st.switch_page("pages/session_detail.py")
    with c_back2:
        if st.button("← Quay lại nhật ký sự kiện", key="btn_back_events"):
            st.session_state["history_active_tab"] = "events"
            st.switch_page("pages/history.py")
else:
    if st.button("← Quay lại danh mục ca thi", key="btn_back_events"):
        st.session_state["history_active_tab"] = "sessions"
        st.switch_page("pages/history.py")


# ── Điều hướng sự kiện trước/sau ────────────────────────────
# Mục đích: giáo viên xác minh liên tiếp mà không phải quay lại danh sách.
nav_ids = st.session_state.get("event_nav_ids") or []
nav_session = st.session_state.get("event_nav_session")
rebuild_nav = not isinstance(nav_ids, list) or event_id not in nav_ids
if (
    not rebuild_nav
    and nav_session is not None
    and from_sess_id is not None
    and nav_session != from_sess_id
):
    rebuild_nav = True
if rebuild_nav:
    st.session_state.pop("event_nav_scope", None)
    if from_sess_id:
        _nav_events = list_session_events(st.session_state.client, from_sess_id, limit=200)
        nav_ids = [e.get("PK_MaSuKien") for e in _nav_events if e.get("PK_MaSuKien")]
    else:
        nav_ids = [event_id] if event_id else []
    st.session_state["event_nav_ids"] = nav_ids
    st.session_state["event_nav_session"] = from_sess_id

nav_pos = nav_ids.index(event_id) if event_id in nav_ids else -1
nav_total = len(nav_ids)
nav_scope = st.session_state.get("event_nav_scope") or (
    f"Ca thi #{from_sess_id}" if from_sess_id else ""
)


def _go_to_event(target_id: int) -> None:
    """Chuyển sang sự kiện kế bên, giữ nguyên ca thi đang xem."""
    st.session_state["event_id"] = target_id
    st.query_params["id"] = str(target_id)
    if from_sess_id:
        st.query_params["from_session"] = str(from_sess_id)
    st.rerun()


if nav_total > 1 and nav_pos >= 0:
    nav_prev, nav_mid, nav_next = st.columns([0.2, 0.6, 0.2], gap="small")
    with nav_prev:
        if st.button("← Sự kiện trước", key="btn_nav_event_prev", disabled=(nav_pos <= 0)):
            _go_to_event(nav_ids[nav_pos - 1])
    with nav_mid:
        st.markdown(
            f"<div style='text-align:center; font-size:12.5px; color:#475569; line-height:38px;'>"
            f"Sự kiện <strong>{nav_pos + 1}</strong>/<strong>{nav_total}</strong>"
            + (f" · {html.escape(str(nav_scope))}" if nav_scope else "")
            + "</div>",
            unsafe_allow_html=True,
        )
    with nav_next:
        if st.button("Sự kiện tiếp →", key="btn_nav_event_next", disabled=(nav_pos >= nav_total - 1)):
            _go_to_event(nav_ids[nav_pos + 1])

# Thông tin thí sinh gắn với sự kiện (nếu có)
_ev_cand = data.get("candidate") or {}
_ev_sess = data.get("session") or {}
if _ev_cand:
    _cand_bits = [f"SBD {_ev_cand.get('SBD') or '—'}", str(_ev_cand.get("HoTen") or "—")]
    if _ev_cand.get("Lop"):
        _cand_bits.append(f"Lớp {_ev_cand['Lop']}")
    if _ev_sess.get("parent_session_id"):
        _cand_bits.append(f"Ca thi #{_ev_sess['parent_session_id']}")
    st.markdown(
        "<div style='font-size:12.5px; color:#334155; background:#f1f5f9; border:1px solid #e2e8f0;"
        " border-radius:8px; padding:7px 11px; margin:2px 0 10px 0;'>"
        "<strong>Thí sinh:</strong> " + html.escape(" · ".join(_cand_bits)) + "</div>",
        unsafe_allow_html=True,
    )


# ── Main Layout ─────────────────────────────────────────────
left_col, right_col = st.columns([1.6, 1], gap="medium")

# ── LEFT: Evidence Image + BBox ─────────────────────────────
with left_col:
    st.markdown(f"""
    <div class="img-card">
        <div class="img-card-header">
            <span class="cam-label">
                Bằng chứng vi phạm #EV-{event_id:02d} — {friendly_label} · {cam_label}
            </span>
            <span class="live-badge"><span class="dot"></span> {conf}%</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    pil_img = None
    if evidences:
        for ev in evidences:
            raw = get_evidence_bytes(st.session_state.client, ev.get("PK_MaBangChung"))
            if not raw:
                continue
            try:
                pil_img = Image.open(io.BytesIO(raw))
            except Exception:
                pil_img = None
                continue
            ev_role = ev.get("VaiTroCamera") or "front"
            ev_cam = "Camera phụ (điện thoại)" if ev_role == "side" else "Camera trước (webcam)"
            st.image(pil_img, use_container_width=True)
            st.caption(
                f"Ảnh minh chứng · {ev_cam} · {str(ev.get('ThoiGianTao', ''))[:19].replace('T', ' ')}"
            )
    if not pil_img:
        notify.warning("Không tải được ảnh bằng chứng của sự kiện này.")

# ── RIGHT: Info + Verify ────────────────────────────────────
with right_col:
    candidate = data.get("candidate") or {}
    session_info = data.get("session") or {}
    if candidate:
        st.markdown(f"""
        <div class="kpi-mini" style="border-left: 3px solid #2563eb;">
            <div class="kpi-left">
                <div class="kpi-label">THÍ SINH</div>
                <div class="kpi-val" style="font-size:15px;">
                    {html.escape(str(candidate.get('SBD') or ''))} · {html.escape(str(candidate.get('HoTen') or ''))}
                    <span style="font-size:12px;font-weight:normal;color:#64748b;">
                        {('· ' + html.escape(str(candidate.get('Lop')))) if candidate.get('Lop') else ''}
                    </span>
                </div>
                <div style="font-size:11px;color:#64748b;margin-top:2px;">
                    Ca thi #{html.escape(str(session_info.get('parent_session_id') or session_info.get('PK_MaPhienGiamSat') or '—'))}
                    · {html.escape(str(session_info.get('PhongThi') or '—'))}
                    · {html.escape(str(session_info.get('MonThi') or '—'))}
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="right-section-title">Thông tin sự kiện</div>', unsafe_allow_html=True)

    user_label = data.get("NhanNguoiDung")
    if trang_thai == "sai":
        user_label_disp = "Bác bỏ (Báo sai)"
    elif user_label:
        user_label_disp = get_friendly_behavior_label(user_label)
    elif trang_thai in ("dung", "da_kiem_tra", "da_xac_minh"):
        user_label_disp = friendly_label
    else:
        user_label_disp = "Chờ kiểm tra"

    st.markdown(f"""
    <div class="kpi-mini">
        <div class="kpi-left">
            <div class="kpi-label">HÀNH VI PHÁT HIỆN (AI)</div>
            <div class="kpi-val red">{friendly_label} <span style="font-size:12px; font-weight:normal; color:#64748b;">({raw_label})</span></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="kpi-mini">
        <div class="kpi-left">
            <div class="kpi-label">ĐỘ TIN CẬY AI</div>
            <div class="kpi-val blue">{conf}%</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="kpi-mini">
        <div class="kpi-left">
            <div class="kpi-label">NGUỒN CAMERA</div>
            <div class="kpi-val">{cam_label}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="kpi-mini">
        <div class="kpi-left">
            <div class="kpi-label">KẾT LUẬN XÁC MINH</div>
            <div class="kpi-val">{user_label_disp}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="kpi-mini">
        <div class="kpi-left">
            <div class="kpi-label">TRẠNG THÁI HIỆN TẠI</div>
            <div class="kpi-val"><span class="{stt_cls}">{stt_text}</span></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="right-section-title">Xác minh nghiệp vụ</div>', unsafe_allow_html=True)

    is_pending = (trang_thai == "cho_kiem_tra")
    if not is_pending:
        # Sự kiện đã được xử lý (xác nhận hoặc bác bỏ) -> Ẩn nút, không cho tương tác nữa
        if trang_thai in ("dung", "da_kiem_tra", "da_xac_minh"):
            st.markdown(
                f"<div style='background:#f0fdf4; border:1px solid #bbf7d0; border-radius:8px; padding:12px 14px; color:#16a34a; font-size:13.5px; font-weight:600; text-align:center; margin-top:8px;'>"
                f"Đã xác nhận Vi phạm: {user_label_disp}"
                f"</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                "<div style='background:#fef2f2; border:1px solid #fecaca; border-radius:8px; padding:12px 14px; color:#dc2626; font-size:13.5px; font-weight:600; text-align:center; margin-top:8px;'>"
                "Đã bác bỏ sự kiện (Báo sai)"
                "</div>",
                unsafe_allow_html=True,
            )
    else:
        # Sự kiện đang chờ kiểm tra -> Cho phép xác nhận vi phạm hoặc bác bỏ
        available_labels = ["Cheat_Paper", "cellphone", "quay_dau", "quay_sau", "cui_xuong", "vang_mat", "nhieu_nguoi"]
        label_names = {
            "Cheat_Paper": "Tài liệu không hợp lệ (Cheat_Paper)",
            "cellphone": "Điện thoại di động (cellphone)",
            "quay_dau": "Quay đầu (>45°)",
            "quay_sau": "Quay người về sau trao đổi bài",
            "cui_xuong": "Cúi đầu nhìn xuống gầm bàn",
            "vang_mat": "Vắng mặt khỏi khung hình (vang_mat)",
            "nhieu_nguoi": "Nhiều người trong khung hình (nhieu_nguoi)",
        }
        cur_choice = data.get("NhanNguoiDung") or data.get("NhanAI") or "Cheat_Paper"
        def_idx = available_labels.index(cur_choice) if cur_choice in available_labels else 0

        chosen_label = st.selectbox(
            "Nhãn xác minh kết luận:",
            options=available_labels,
            index=def_idx,
            format_func=lambda x: label_names.get(x, x),
            key=f"detail_sel_label_{event_id}",
        )

        col_ok, col_no = st.columns(2)
        with col_ok:
            if st.button("Xác nhận Vi phạm", use_container_width=True, type="primary"):
                res = verify_event(st.session_state.client, event_id, "dung", chosen_label)
                if res is not None and res.status_code == 200:
                    notify.defer_success(f"Đã xác nhận sự kiện với nhãn: {label_names.get(chosen_label, chosen_label)}")
                    st.rerun()
                else:
                    notify.error("Lỗi khi gửi xác minh tới hệ thống")
        with col_no:
            if st.button("Bác bỏ (Báo sai)", use_container_width=True):
                res = verify_event(st.session_state.client, event_id, "sai", "")
                if res is not None and res.status_code == 200:
                    notify.defer_success("Đã ghi nhận bác bỏ sự kiện (Báo sai)")
                    st.rerun()
                else:
                    notify.error("Lỗi khi gửi xác minh tới hệ thống")

