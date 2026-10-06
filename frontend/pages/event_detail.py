import base64
import io

import streamlit as st
from utils.notify import notify
from PIL import Image

from config import API_BASE_URL
from services.event_api import get_event_detail, get_evidence_bytes, verify_event
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
st.markdown(load_css("styles/frame_detail.css"), unsafe_allow_html=True)

# ── Event ID & Session ID ───────────────────────────────────
if "id" in st.query_params:
    try:
        st.session_state["event_id"] = int(st.query_params["id"])
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

friendly_label = get_friendly_behavior_label(raw_label)
stt_text, stt_cls = get_event_status_info(trang_thai)

# ── Header ──────────────────────────────────────────────────
render_page_header(f"Chi tiết sự kiện #EV-{event_id:02d}", active="history")

if from_sess_id:
    c_back1, c_back2, _ = st.columns([1.5, 1.5, 3])
    with c_back1:
        if st.button("← Quay lại chi tiết ca thi", key="btn_back_session"):
            st.session_state["selected_session"] = from_sess_id
            st.session_state["session_id"] = from_sess_id
            st.query_params["id"] = str(from_sess_id)
            if "from_session" in st.query_params:
                del st.query_params["from_session"]
            st.switch_page("pages/session_detail.py")
    with c_back2:
        if st.button("Quay lại nhật ký sự kiện", key="btn_back_events"):
            st.session_state["history_active_tab"] = "events"
            st.switch_page("pages/history.py")
else:
    if st.button("← Quay lại danh mục ca thi", key="btn_back_events"):
        st.session_state["history_active_tab"] = "sessions"
        st.switch_page("pages/history.py")


# ── Main Layout ─────────────────────────────────────────────
left_col, right_col = st.columns([1.6, 1], gap="medium")

# ── LEFT: Evidence Image + BBox ─────────────────────────────
with left_col:
    st.markdown(f"""
    <div class="img-card">
        <div class="img-card-header">
            <span class="cam-label">
                Bằng chứng vi phạm #EV-{event_id:02d} — {friendly_label}
            </span>
            <span class="live-badge"><span class="dot"></span> {conf}%</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    pil_img = None
    if evidences:
        raw = get_evidence_bytes(st.session_state.client, evidences[0].get("PK_MaBangChung"))
        if raw:
            try:
                pil_img = Image.open(io.BytesIO(raw))
            except Exception:
                pass

    if pil_img:
        st.image(pil_img, use_container_width=True)
        st.caption("Khung nhận diện vi phạm được hệ thống camera AI đánh dấu tại thời điểm phát hiện.")
    else:
        notify.warning("Không tải được ảnh bằng chứng của sự kiện này.")

# ── RIGHT: Info + Verify ────────────────────────────────────
with right_col:
    st.markdown('<div class="right-section-title">Thông tin sự kiện</div>', unsafe_allow_html=True)

    user_label = data.get("NhanNguoiDung")
    user_label_disp = get_friendly_behavior_label(user_label) if user_label else "Chưa xác minh"

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

    available_labels = ["Cheat_Paper", "cellphone", "quay_dau", "quay_sau", "cui_xuong", "Answer_paper"]
    label_names = {
        "Cheat_Paper": "Tài liệu giấy (Cheat_Paper)",
        "cellphone": "Điện thoại di động (cellphone)",
        "quay_dau": "Quay đầu (>45°)",
        "quay_sau": "Quay người về sau trao đổi bài",
        "cui_xuong": "Cúi đầu nhìn xuống gầm bàn",
        "Answer_paper": "Giấy thi hợp lệ (Answer_paper - Không vi phạm)",
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
            res = verify_event(st.session_state.client, event_id, "sai", "Answer_paper")
            if res is not None and res.status_code == 200:
                notify.defer_success("Đã ghi nhận bác bỏ sự kiện (Báo sai: Giấy thi hợp lệ)")
                st.rerun()
            else:
                notify.error("Lỗi khi gửi xác minh tới hệ thống")

