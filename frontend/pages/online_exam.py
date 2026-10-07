"""Trang Thi online (FR-online): nhập DS thí sinh, lưới giám thị theo ca thi."""

import streamlit as st
from streamlit_autorefresh import st_autorefresh

from config import API_BASE_URL
from services.candidate_api import exam_overview, import_candidates, list_candidates
from services.history_api import get_history
from utils.auth_guard import require_auth
from utils.hide_streamlit_sidebar import hide_sidebar
from utils.http import init_session_state
from utils.load_css import load_css
from utils.notify import notify
from utils.render_header import render_page_header

# ── Cấu hình trang ──────────────────────────────────────────
st.set_page_config(layout="wide", initial_sidebar_state="collapsed", page_title="Thi online")

# ── Styles & Header ─────────────────────────────────────────
hide_sidebar()
st.markdown(load_css("styles/sidebar.css"), unsafe_allow_html=True)
st.markdown(load_css("styles/app_theme.css"), unsafe_allow_html=True)

init_session_state()
require_auth()

render_page_header("Thi online", active="online_exam")

# ── Chọn ca thi (phiên phòng) ───────────────────────────────
sessions = get_history(st.session_state.client, limit=50) or []
if not sessions:
    notify.info("Chưa có ca thi nào. Mở ca thi ở trang Giám sát trước.")
    st.stop()

sess_options = {
    s["PK_MaPhienGiamSat"]: f"#{s['PK_MaPhienGiamSat']} - {s.get('PhongThi') or ''} {s.get('MonThi') or ''}".strip()
    for s in sessions
}
sel_id = st.selectbox(
    "Ca thi",
    options=list(sess_options.keys()),
    format_func=lambda x: sess_options.get(x, f"#{x}"),
    key="online_exam_session",
)

# ── Nhập danh sách thí sinh ─────────────────────────────────
with st.expander("Nhập danh sách thí sinh (SBD, Họ tên, Lớp)", expanded=False):
    st.caption("Mỗi dòng một thí sinh, cách nhau bằng dấu phẩy. Ví dụ: TS001, Nguyễn Văn A, 12A1")
    raw = st.text_area("Danh sách", height=120, key="online_import_text")
    if st.button("Nhập danh sách", type="primary", key="online_import_btn"):
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
            notify.warning("Chưa có dòng hợp lệ nào (cần ít nhất SBD, Họ tên).")
        else:
            res = import_candidates(st.session_state.client, sel_id, items)
            if res is not None and res.status_code == 200:
                notify.success(f"Đã nhập {len(res.json())} thí sinh vào ca #{sel_id}.")
                st.rerun()
            else:
                notify.error("Nhập danh sách thất bại.")

# ── Link trang thi cho thí sinh ─────────────────────────────
exam_url = f"{API_BASE_URL}/exam"
st.info(f"Thí sinh mở trang thi tại: {exam_url} rồi chỉ cần nhập SBD.")

# ── Lưới giám thị ───────────────────────────────────────────
st.markdown("### Lưới giám thị")
rows = exam_overview(st.session_state.client, sel_id)
if not rows:
    notify.info("Ca này chưa có thí sinh nào. Nhập danh sách ở trên.")
else:
    cols = st.columns(4)
    for i, c in enumerate(rows):
        with cols[i % 4]:
            dot = "🟢" if c.get("dang_giam_sat") else "⚪"
            alert = f"🚨 {c.get('cho_kiem_tra', 0)} chờ" if c.get("cho_kiem_tra") else "yên tĩnh"
            st.markdown(
                f"**{dot} {c.get('SBD')} - {c.get('HoTen')}**  \n"
                f"{c.get('Lop') or ''} · {alert} · tổng {c.get('tong_su_kien', 0)} sự kiện"
            )
            if st.button("Chi tiết", key=f"online_ev_{c['PK_MaThiSinh']}"):
                sid = c.get("PK_MaPhienGiamSat")
                if sid:
                    st.session_state["selected_session"] = sid
                    st.switch_page("pages/session_detail.py")

st_autorefresh(interval=10000, key="online_grid_refresh")
