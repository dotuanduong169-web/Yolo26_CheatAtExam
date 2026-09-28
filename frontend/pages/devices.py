# -*- coding: utf-8 -*-
"""Trang quản lý thiết bị biên: đăng ký camera/đầu ghi RTSP, sửa, xóa."""

import streamlit as st

from components.app_sidebar import render_sidebar
from services.device_api import create_device, delete_device, list_devices, update_device
from utils.auth_guard import require_auth
from utils.hide_streamlit_sidebar import hide_sidebar
from utils.http import init_session_state
from utils.load_css import load_css
from utils.render_header import render_page_header

# ── Config ──────────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="Thiết bị")

init_session_state()
require_auth()

# ── Sidebar & Styles ────────────────────────────────────────
hide_sidebar()
render_sidebar(active="devices")
st.markdown(load_css("styles/sidebar.css"), unsafe_allow_html=True)
st.markdown(load_css("styles/history.css"), unsafe_allow_html=True)
st.markdown("""
<style>
.badge { display:inline-block; padding:3px 10px; border-radius:20px; font-size:11px; font-weight:700; }
.badge-normal { background:#dcfce7; color:#16a34a; }
.badge-warning { background:#fff7ed; color:#ea580c; }
</style>
""", unsafe_allow_html=True)

# ── Header ──────────────────────────────────────────────────
render_page_header("Quản lý thiết bị")

client = st.session_state.client
is_admin = st.session_state.get("user_role") == "admin"

# ── Register Form (admin) ───────────────────────────────────
if is_admin:
    with st.expander("➕ Đăng ký thiết bị mới", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("Tên thiết bị", placeholder="VD: Cam P101")
            rtsp = st.text_input("Đường dẫn RTSP", placeholder="0 (webcam) hoặc rtsp://...")
        with c2:
            location = st.text_input("Vị trí", placeholder="VD: Phòng 101 - góc trái")
            st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
            if st.button("Đăng ký", type="primary", use_container_width=True):
                if not name or not rtsp:
                    st.warning("⚠️ Nhập tên và đường dẫn RTSP")
                else:
                    res = create_device(client, name.strip(), rtsp.strip(), (location or "").strip())
                    if res is not None and res.status_code == 200:
                        st.toast("✅ Đăng ký thành công")
                        st.rerun()
                    else:
                        st.error("❌ Lỗi đăng ký thiết bị")

# ── Table ───────────────────────────────────────────────────
devices = list_devices(client)

st.markdown('<div class="table-card">', unsafe_allow_html=True)
st.markdown("""
<div class="table-header-row">
    <span>ID</span>
    <span>TÊN THIẾT BỊ</span>
    <span>RTSP</span>
    <span>TRẠNG THÁI</span>
    <span style="text-align:right">THAO TÁC</span>
</div>
""", unsafe_allow_html=True)

if not devices:
    st.markdown("""
    <div style="padding:40px 24px; text-align:center; color:#9ca3af;">
        <div style="font-size:14px; font-weight:500;">Chua co thiet bi nao</div>
    </div>
    """, unsafe_allow_html=True)
else:
    for dev in devices:
        did = dev["PK_MaThietBi"]
        row = st.columns([0.6, 2, 2, 1.2, 1])
        with row[0]:
            st.markdown(f'<span class="cell-session-id">#{did}</span>', unsafe_allow_html=True)
        with row[1]:
            st.markdown(
                f'<span class="cell-class">{dev.get("TenThietBi", "")}</span><br>'
                f'<span style="color:#94a3b8;font-size:12px">{dev.get("MoTaViTri") or ""}</span>',
                unsafe_allow_html=True,
            )
        with row[2]:
            st.markdown(f'<span class="cell-date">{dev.get("DuongDanRTSP", "")}</span>', unsafe_allow_html=True)
        with row[3]:
            stt = dev.get("TrangThai", "")
            cls = "badge-normal" if stt == "san_sang" else "badge-warning"
            st.markdown(f"<span class='badge {cls}'>{stt}</span>", unsafe_allow_html=True)
        with row[4]:
            if is_admin:
                with st.popover("⋮", use_container_width=False):
                    if st.button("Bật/Tắt", key=f"tg_{did}", use_container_width=True):
                        new_stt = "tat" if dev.get("TrangThai") != "tat" else "san_sang"
                        res = update_device(client, did, {"TrangThai": new_stt})
                        if res is not None and res.status_code == 200:
                            st.toast("✅ Đã cập nhật")
                            st.rerun()
                        else:
                            st.error("❌ Lỗi cập nhật")
                    if st.button("Xóa", key=f"del_{did}", use_container_width=True):
                        res = delete_device(client, did)
                        if res is not None and res.status_code == 200:
                            st.toast("✅ Đã xóa")
                            st.rerun()
                        else:
                            detail = ""
                            try:
                                detail = res.json().get("detail", "")
                            except Exception:
                                pass
                            st.error(f"❌ Không xóa được. {detail}")

st.markdown("</div>", unsafe_allow_html=True)

if not is_admin:
    st.caption("Chỉ admin được đăng ký/sửa/xóa thiết bị.")
