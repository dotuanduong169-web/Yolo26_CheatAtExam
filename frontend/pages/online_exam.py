"""Trang Thi online (FR-online): nhập DS thí sinh, lưới giám thị theo ca thi."""

import streamlit as st
from streamlit_autorefresh import st_autorefresh

from config import API_BASE_URL
from services.candidate_api import (
    close_session,
    create_online_session,
    exam_overview,
    extract_error_detail,
    get_candidate_snapshot,
    import_candidates,
    list_candidates,
    open_session,
)
from services.history_api import get_history
from utils.auth_guard import require_auth
from utils.hide_streamlit_sidebar import hide_sidebar
from utils.http import cache_invalidate, init_session_state
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

# Hỗ trợ tạo nhanh ca thi online mới
with st.expander("➕ Tạo ca thi online mới", expanded=not bool(sessions)):
    col_cr, col_cs, col_cb = st.columns([2, 2, 1])
    with col_cr:
        new_room = st.text_input("Phòng thi", placeholder="VD: P.Online-101", key="new_room_inp")
    with col_cs:
        new_subj = st.text_input("Môn thi", placeholder="VD: Toán học", key="new_subj_inp")
    with col_cb:
        st.write("")
        st.write("")
        if st.button("Tạo ca thi", type="primary", key="btn_create_online"):
            if not (new_room or "").strip() or not (new_subj or "").strip():
                notify.warning("Vui lòng điền đủ phòng thi và môn thi.")
            else:
                resp = create_online_session(st.session_state.client, new_room.strip(), new_subj.strip())
                if resp is not None and resp.status_code == 200:
                    created_data = resp.json()
                    new_id = created_data.get("PK_MaPhienGiamSat")
                    cache_invalidate("hist:")
                    notify.success(f"Đã tạo ca thi #{new_id} ({new_room} - {new_subj}).")
                    st.session_state["online_exam_session"] = new_id
                    st.rerun()
                else:
                    err_msg = extract_error_detail(resp, default="Tạo ca thi thất bại")
                    notify.error(err_msg, title="Lỗi tạo ca thi")

if not sessions:
    notify.info("Chưa có ca thi nào. Bạn hãy tạo ca thi mới ở trên.")
    st.stop()

sess_dict = {s["PK_MaPhienGiamSat"]: s for s in sessions}

if "online_exam_session" in st.session_state and st.session_state["online_exam_session"] not in sess_dict:
    st.session_state["online_exam_session"] = list(sess_dict.keys())[0]


def _format_sess(sid):
    s = sess_dict.get(sid, {})
    stt = s.get("TrangThai")
    icon = "🟢" if stt == "dang_giam_sat" else "🔴"
    stt_text = "Đang mở" if stt == "dang_giam_sat" else "Đã đóng"
    return f"{icon} #{sid} - {s.get('PhongThi') or ''} {s.get('MonThi') or ''} ({stt_text})".strip()


col_select, col_action = st.columns([3, 1])
with col_select:
    sel_id = st.selectbox(
        "Ca thi",
        options=list(sess_dict.keys()),
        format_func=_format_sess,
        key="online_exam_session",
    )

curr_sess = sess_dict.get(sel_id, {})
is_open = curr_sess.get("TrangThai") == "dang_giam_sat"

with col_action:
    st.write("")
    st.write("")
    if is_open:
        if st.button("🔴 Kết thúc ca thi", key=f"btn_close_sess_{sel_id}"):
            res = close_session(st.session_state.client, sel_id)
            if res is not None and res.status_code == 200:
                cache_invalidate("hist:")
                notify.success(f"Đã kết thúc ca thi #{sel_id}.")
                st.rerun()
            else:
                err_msg = extract_error_detail(res, default="Không thể kết thúc ca thi")
                notify.error(err_msg, title="Lỗi kết thúc ca thi")
    else:
        if st.button("🟢 Mở ca thi", type="primary", key=f"btn_open_sess_{sel_id}"):
            res = open_session(st.session_state.client, sel_id)
            if res is not None and res.status_code == 200:
                cache_invalidate("hist:")
                notify.success(f"Đã mở ca thi #{sel_id}! Thí sinh có thể vào phòng thi.")
                st.rerun()
            else:
                err_msg = extract_error_detail(res, default="Không thể mở ca thi")
                notify.error(err_msg, title="Lỗi mở ca thi")

# ── Link trang thi cho thí sinh ─────────────────────────────
exam_url = f"{API_BASE_URL}/exam?session_id={sel_id}"
if is_open:
    st.info(f"✅ **Ca thi đang mở**: Thí sinh mở link [**{exam_url}**]({exam_url}) rồi chỉ cần nhập SBD để vào thi.")
else:
    st.warning(f"⚠️ **Ca thi #{sel_id} đang ĐÓNG**: Thí sinh sẽ không vào được nếu bạn chưa bấm **'🟢 Mở ca thi'** ở trên.")
    st.caption(f"Đường dẫn dự thi: {exam_url}")

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
                msg = f"Đã nhập {len(res.json())} thí sinh vào ca #{sel_id}."
                if not is_open:
                    msg += " Hãy nhớ bấm '🟢 Mở ca thi' để thí sinh có thể vào thi."
                notify.success(msg)
                st.rerun()
            else:
                notify.error("Nhập danh sách thất bại.")

# ── Lưới giám thị ───────────────────────────────────────────
st.markdown("### Lưới giám thị")

rows = exam_overview(st.session_state.client, sel_id)
if not rows:
    notify.info("Ca này chưa có thí sinh nào. Nhập danh sách ở trên.")
else:
    CHUNK_SIZE = 4
    for chunk_idx in range(0, len(rows), CHUNK_SIZE):
        chunk = rows[chunk_idx : chunk_idx + CHUNK_SIZE]
        cols = st.columns(CHUNK_SIZE)
        for col_idx, c in enumerate(chunk):
            with cols[col_idx]:
                is_active = c.get("dang_giam_sat")
                dot = "🟢" if is_active else "⚪"
                status_text = "Đang thi" if is_active else ("Đã dừng" if c.get("PK_MaPhienGiamSat") else "Chưa vào")
                alert = f"🚨 {c.get('cho_kiem_tra', 0)} chờ" if c.get("cho_kiem_tra") else "yên tĩnh"
                sid = c.get("PK_MaPhienGiamSat")

                st.markdown(
                    f"**{dot} {c.get('SBD')} - {c.get('HoTen')}**  \n"
                    f"{c.get('Lop') or ''} · *{status_text}* · {alert} · {c.get('tong_su_kien', 0)} sự kiện"
                )

                # Hiển thị ảnh snapshot cắt lên giao diện
                if sid:
                    snap_bytes = get_candidate_snapshot(st.session_state.client, sid)
                    if snap_bytes:
                        st.image(snap_bytes, use_container_width=True)
                    else:
                        if is_active:
                            st.caption("📷 Đang chờ frame camera...")
                        else:
                            st.caption("📷 Chưa có ảnh vi phạm")
                else:
                    st.caption("⏳ Thí sinh chưa vào phòng thi")

                if st.button("Chi tiết", key=f"online_ev_{c['PK_MaThiSinh']}", use_container_width=True):
                    if sid:
                        st.session_state["selected_session"] = sid
                        st.session_state["detail_return_to"] = "online_exam"
                        st.switch_page("pages/session_detail.py")
                    else:
                        notify.info(f"Thí sinh {c.get('HoTen')} ({c.get('SBD')}) chưa vào thi, chưa có dữ liệu phiên.")

st_autorefresh(interval=10000, key="online_grid_refresh")
