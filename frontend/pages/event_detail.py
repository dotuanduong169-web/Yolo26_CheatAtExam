"""Trang chi tiết sự kiện: xem ảnh bằng chứng, vẽ bbox, xác minh đúng/sai."""

import base64
import io

import streamlit as st
from PIL import Image

from components.app_sidebar import render_sidebar
from config import API_BASE_URL
from services.event_api import get_event_detail, get_evidence_bytes, verify_event
from utils.auth_guard import require_auth
from utils.hide_streamlit_sidebar import hide_sidebar
from utils.http import init_session_state
from utils.load_css import load_css
from utils.render_header import render_page_header

# ── Config ──────────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="Chi tiết sự kiện")

init_session_state()
require_auth()

# ── Sidebar & Styles ───────────────────────────────────────
hide_sidebar()
render_sidebar(active="events")
st.markdown(load_css("styles/sidebar.css"), unsafe_allow_html=True)
st.markdown(load_css("styles/frame_detail.css"), unsafe_allow_html=True)

# ── Event ID ────────────────────────────────────────────────
event_id = st.session_state.get("event_id")
if not event_id:
    st.warning("Không có sự kiện để xem.")
    st.stop()


# ── Load Data ───────────────────────────────────────────────
data = get_event_detail(st.session_state.client, event_id)
if not data:
    st.error("Không lấy được dữ liệu sự kiện.")
    st.stop()

label = data.get("LoaiHanhVi", "?")
conf = round(float(data.get("DoTinCay", 0)) * 100, 1)
trang_thai = data.get("TrangThaiKiemTra", "cho_kiem_tra")
bbox = data.get("ToaDo") or []
evidences = data.get("evidences", [])

# ── Header ──────────────────────────────────────────────────
render_page_header(f"Chi tiết sự kiện #{event_id}")

if st.button("← Quay lại danh sách sự kiện"):
    st.switch_page("pages/events.py")

# ── Main Layout ─────────────────────────────────────────────
left_col, right_col = st.columns([1.6, 1], gap="medium")

# ── LEFT: Evidence Image + BBox ─────────────────────────────
with left_col:
    st.markdown(f"""
    <div class="img-card">
        <div class="img-card-header">
            <span class="cam-label">
                <span class="icon">📹</span>
                Bằng chứng #{event_id} — {label}
            </span>
            <span class="live-badge"><span class="dot"></span> {conf}%</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    img_b64 = None
    img_w, img_h = 1, 1
    if evidences:
        raw = get_evidence_bytes(st.session_state.client, evidences[0].get("PK_MaBangChung"))
        if raw:
            try:
                pil_img = Image.open(io.BytesIO(raw))
                img_w, img_h = pil_img.size
                img_b64 = base64.b64encode(raw).decode()
            except Exception:
                pass

    has_bbox = img_b64 and isinstance(bbox, list) and len(bbox) == 4

    if has_bbox:
        x1, y1, x2, y2 = bbox
        left_pct = (x1 / img_w) * 100
        top_pct = (y1 / img_h) * 100
        width_pct = ((x2 - x1) / img_w) * 100
        height_pct = ((y2 - y1) / img_h) * 100

        import streamlit.components.v1 as components

        component_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: transparent; }}
            .interactive-frame {{ position: relative; width: 100%; border-radius: 14px; overflow: hidden; background: #0a0a0a; }}
            .interactive-frame > img {{ width: 100%; display: block; }}
            .bbox-overlay {{ position: absolute; border: 2.5px solid #ef4444; border-radius: 6px; background: rgba(239, 68, 68, 0.12); z-index: 2; }}
            .bbox-tag {{ position: absolute; top: -24px; left: -2px; padding: 3px 10px; border-radius: 6px 6px 0 0;
                         font-size: 11px; font-weight: 700; white-space: nowrap; background: #ef4444; color: #fff; }}
            .frame-hint {{ display: flex; align-items: center; justify-content: center; gap: 6px; margin-top: 10px;
                           padding: 8px 16px; background: linear-gradient(135deg, #eff6ff, #eef2ff);
                           border: 1px solid #c7d2fe; border-radius: 10px; font-size: 12px; font-weight: 600; color: #4f46e5; }}
        </style>
        </head>
        <body>
            <div class="interactive-frame">
                <img src="data:image/jpeg;base64,{img_b64}" alt="Evidence">
                <div class="bbox-overlay"
                     style="left:{left_pct:.2f}%; top:{top_pct:.2f}%;
                            width:{width_pct:.2f}%; height:{height_pct:.2f}%;">
                    <span class="bbox-tag">{label} · {conf}%</span>
                </div>
            </div>
            <div class="frame-hint"><span>🔍</span> Dùng nút bên phải để xác minh đúng/sai</div>
        </body>
        </html>
        """

        aspect = img_h / img_w if img_w > 0 else 0.75
        estimated_height = int(700 * aspect) + 60
        components.html(component_html, height=estimated_height, scrolling=False)
    elif img_b64:
        st.image(f"data:image/jpeg;base64,{img_b64}", use_container_width=True)
    else:
        st.warning("Không tải được ảnh bằng chứng.")

# ── RIGHT: Info + Verify ────────────────────────────────────
with right_col:
    st.markdown('<div class="right-section-title">Thông tin sự kiện</div>', unsafe_allow_html=True)

    st.markdown(f"""
    <div class="kpi-mini">
        <div class="kpi-left">
            <div class="kpi-label">LOẠI HÀNH VI</div>
            <div class="kpi-val red">{label}</div>
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
            <div class="kpi-label">NHÃN AI / NHÃN SỬA</div>
            <div class="kpi-val">{data.get("NhanAI", "?")} / {data.get("NhanNguoiDung") or "—"}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="kpi-mini">
        <div class="kpi-left">
            <div class="kpi-label">TRẠNG THÁI</div>
            <div class="kpi-val">{trang_thai}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="right-section-title">Xác minh thủ công</div>', unsafe_allow_html=True)
    col_ok, col_no = st.columns(2)
    with col_ok:
        if st.button("✅ Đúng", use_container_width=True, type="primary"):
            res = verify_event(st.session_state.client, event_id, "dung", "")
            if res is not None and res.status_code == 200:
                st.toast("✅ Đã xác nhận đúng")
                st.rerun()
            else:
                st.error("❌ Lỗi xác minh")
    with col_no:
        if st.button("❌ Sai", use_container_width=True):
            st.session_state["show_fix_label"] = True

    if st.session_state.get("show_fix_label"):
        fix_label = st.selectbox("Nhãn đúng là", ["Answer_paper", "Cheat_Paper", "cellphone", "quay_dau", "quay_sau", "cui_xuong", "nhin_thang"])
        if st.button("Lưu xác minh sai", use_container_width=True):
            res = verify_event(st.session_state.client, event_id, "sai", fix_label)
            if res is not None and res.status_code == 200:
                st.session_state["show_fix_label"] = False
                st.toast("✅ Đã ghi nhận sai")
                st.rerun()
            else:
                st.error("❌ Lỗi xác minh")
