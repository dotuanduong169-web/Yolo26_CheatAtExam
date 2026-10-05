"""Trang Thiết bị biên & Hệ thống (FR04): Quản lý camera IP/RTSP và tài nguyên biên."""

import streamlit as st
from utils.notify import notify

from services.device_api import (
    create_device,
    delete_device,
    list_devices,
    test_device,
    update_device,
)
from utils.auth_guard import require_auth
from utils.hide_streamlit_sidebar import hide_sidebar
from utils.http import init_session_state
from utils.load_css import load_css
from utils.render_header import render_page_header
from utils.status_helpers import get_device_status_badge

# ── Cấu hình trang ──────────────────────────────────────────
st.set_page_config(layout="wide", initial_sidebar_state="collapsed", page_title="Thiết bị biên")

init_session_state()
require_auth()

# ── Styles & Header ─────────────────────────────────────────
hide_sidebar()
st.markdown(load_css("styles/sidebar.css"), unsafe_allow_html=True)
st.markdown(load_css("styles/app_theme.css"), unsafe_allow_html=True)
render_page_header("Thiết bị biên", active="devices")

# ── 3 Khung đo đạc tài nguyên biên (Wireframe Grid-3) ───────
is_running = st.session_state.get("running", False)
fps_val = "24.5 FPS" if is_running else "0.0 FPS"
fps_hint = "Trạng thái: Luồng đang suy luận" if is_running else "Khuyến nghị: > 20 FPS"
gpu_val = "48 %" if is_running else "4 %"

st.markdown(f"""
<div class="wf-grid-3">
    <div class="wf-stat-tile">
        <div class="wf-stat-label">Tốc độ xử lý biên (FPS)</div>
        <div class="wf-stat-num">{fps_val}</div>
        <div class="wf-stat-hint">{fps_hint}</div>
    </div>
    <div class="wf-stat-tile">
        <div class="wf-stat-label">Tải tính toán (GPU / NPU)</div>
        <div class="wf-stat-num">{gpu_val}</div>
        <div class="wf-stat-hint">Nền tảng biên: NVIDIA Jetson Orin / OpenVINO</div>
    </div>
    <div class="wf-stat-tile">
        <div class="wf-stat-label">Bộ nhớ đệm (Circular Buffer)</div>
        <div class="wf-stat-num">1 Frame</div>
        <div class="wf-stat-hint">Cơ chế ghi đè liên tục chống tràn RAM thiết bị biên</div>
    </div>
</div>
""", unsafe_allow_html=True)

client = st.session_state.client
is_admin = st.session_state.get("user_role") == "admin"

# ── Dialogs cho thao tác Thiết bị biên ───────────────────────
@st.dialog("Đăng ký thiết bị camera IP / RTSP mới")
def create_device_dialog():
    new_name = st.text_input("Tên thiết bị", placeholder="VD: Jetson Orin - Cam 01")
    new_rtsp = st.text_input("Đường dẫn luồng RTSP / Camera index", placeholder="rtsp://192.168.1.120:554/stream1 hoặc 0")
    new_loc = st.text_input("Vị trí lắp đặt phòng thi", placeholder="VD: Phòng P.302 (Chính diện)")

    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Hủy bỏ", use_container_width=True):
            st.rerun()
    with c2:
        if st.button("Lưu thiết bị mới", type="primary", use_container_width=True):
            if not new_name.strip() or not new_rtsp.strip():
                notify.warning("Vui lòng điền đầy đủ tên thiết bị và đường dẫn RTSP")
            else:
                res = create_device(client, new_name.strip(), new_rtsp.strip(), new_loc.strip())
                if res and res.status_code == 200:
                    notify.success("Đăng ký thiết bị thành công")
                    st.rerun()
                else:
                    notify.error("Lỗi khi thêm thiết bị")


@st.dialog("Chỉnh sửa thông tin thiết bị")
def edit_device_dialog(dev_id: int, cur_name: str, cur_rtsp: str, cur_loc: str):
    e_name = st.text_input("Tên thiết bị", value=cur_name)
    e_rtsp = st.text_input("Đường dẫn RTSP", value=cur_rtsp)
    e_loc = st.text_input("Vị trí lắp đặt", value=cur_loc)

    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Hủy bỏ", use_container_width=True):
            st.rerun()
    with c2:
        if st.button("Lưu thay đổi", type="primary", use_container_width=True):
            up_res = update_device(client, dev_id, {
                "TenThietBi": e_name.strip(),
                "DuongDanRTSP": e_rtsp.strip(),
                "MoTaViTri": e_loc.strip(),
            })
            if up_res and up_res.status_code == 200:
                notify.success("Đã cập nhật thiết bị thành công")
                st.rerun()
            else:
                notify.error("Lỗi khi cập nhật thiết bị")


@st.dialog("Xác nhận xóa thiết bị")
def delete_device_dialog(dev_id: int, dev_name: str):
    notify.inline(
        f"Bạn có chắc chắn muốn xóa thiết bị <strong>{dev_name}</strong> (#{dev_id})? Lưu ý: Không thể xóa thiết bị đang được gắn với ca thi hoặc có phiên giám sát lịch sử.",
        kind="warning",
        title="Xác nhận xóa thiết bị"
    )
    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        if st.button("Hủy bỏ", use_container_width=True):
            st.rerun()
    with col_d2:
        if st.button("Xác nhận xóa", type="primary", use_container_width=True):
            del_res = delete_device(client, dev_id)
            if del_res is not None and del_res.status_code == 200:
                notify.success(f"Đã xóa thiết bị #{dev_id} thành công!")
                st.rerun()
            elif del_res is not None and del_res.status_code == 400:
                notify.error("Không thể xóa thiết bị đang gắn ca thi hoặc có phiên giám sát.")
            else:
                err_text = del_res.text if del_res else "Lỗi kết nối máy chủ"
                notify.error(f"Xóa thiết bị thất bại: {err_text}")


# ── Danh mục Camera & Thiết bị biên ─────────────────────────
devices = list_devices(client)

# Header bảng kèm nút Thêm mới
h_col1, h_col2 = st.columns([3.2, 1])
with h_col1:
    st.markdown(f"""
    <div class="wf-box" style="margin-bottom: 0;">
        <div class="wf-box-header">
            <div class="wf-box-title">Danh mục thiết bị biên & camera</div>
            <span class="wf-badge">Tổng thiết bị: {len(devices)}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

with h_col2:
    if is_admin:
        if st.button("+ Thêm thiết bị mới", type="primary", use_container_width=True):
            create_device_dialog()

if not devices:
    notify.empty_state("Chưa có thiết bị camera nào trong danh mục", "Vui lòng bấm nút '+ Thêm thiết bị mới' ở góc trên để cấu hình camera vào hệ thống.")
else:
    # Header hàng bảng
    th1, th2, th3, th4, th5, th6 = st.columns([0.8, 1.6, 2.2, 1.6, 1.0, 1.8])
    th1.caption("MÃ TB")
    th2.caption("TÊN THIẾT BỊ")
    th3.caption("ĐƯỜNG DẪN RTSP")
    th4.caption("VỊ TRÍ LẮP ĐẶT")
    th5.caption("TRẠNG THÁI")
    th6.markdown('<div style="text-align:right; font-size:11.5px; font-weight:700; color:#64748b; letter-spacing:0.5px;">THAO TÁC</div>', unsafe_allow_html=True)

    st.markdown("<hr style='margin: 4px 0 8px 0; border: none; border-top: 1px solid var(--wf-border);'>", unsafe_allow_html=True)

    for dev in devices:
        dev_id = dev.get("PK_MaThietBi")
        name = dev.get("TenThietBi", "Camera")
        rtsp = dev.get("DuongDanRTSP", "0")
        loc = dev.get("MoTaViTri") or "Chưa cấu hình"
        status = dev.get("TrangThai", "san_sang")
        stt_badge = get_device_status_badge(status)

        with st.container():
            c1, c2, c3, c4, c5, c6 = st.columns([0.8, 1.6, 2.2, 1.6, 1.0, 1.8])
            with c1:
                st.markdown(f"**#{dev_id}**")
            with c2:
                st.markdown(f"**{name}**")
            with c3:
                st.code(rtsp, language=None)
            with c4:
                st.caption(loc)
            with c5:
                st.markdown(stt_badge, unsafe_allow_html=True)
            with c6:
                if is_admin:
                    b1, b2, b3 = st.columns(3)
                    with b1:
                        if st.button("Kiểm tra", key=f"dev_test_{dev_id}", help="Kiểm tra kết nối camera RTSP"):
                            test_res = test_device(client, dev_id)
                            if test_res.get("online"):
                                lat = test_res.get("latency_ms", 5)
                                notify.success(f"Thiết bị #{dev_id}: {test_res.get('message')} ({lat}ms)")
                            else:
                                notify.error(f"Thiết bị #{dev_id}: {test_res.get('message')}")
                    with b2:
                        if st.button("Sửa", key=f"dev_edit_{dev_id}", help="Chỉnh sửa thông tin thiết bị"):
                            edit_device_dialog(dev_id, name, rtsp, loc if loc != "Chưa cấu hình" else "")
                    with b3:
                        if st.button("Xóa", key=f"dev_del_{dev_id}", help="Xóa thiết bị khỏi danh mục"):
                            delete_device_dialog(dev_id, name)
                else:
                    st.caption("Cán bộ")

            st.markdown("<hr style='margin: 4px 0 10px 0; border: none; border-top: 1px solid var(--wf-border);'>", unsafe_allow_html=True)

# ── Đăng ký thiết bị biên mới (Dành cho Admin) ──────────────
if is_admin:
    with st.expander("Đăng ký thiết bị camera IP / RTSP mới", expanded=False):
        c_name, c_rtsp = st.columns(2)
        with c_name:
            new_name = st.text_input("Tên thiết bị :red[(*)]", placeholder="VD: Jetson Orin - Cam 01")
        with c_rtsp:
            new_rtsp = st.text_input("Đường dẫn luồng RTSP / Camera index :red[(*)]", placeholder="rtsp://192.168.1.120:554/stream1 hoặc 0")

        new_loc = st.text_input("Vị trí lắp đặt phòng thi", placeholder="VD: Phòng P.302 (Chính diện)")

        if st.button("Lưu thiết bị mới", type="primary"):
            if not new_name or not new_rtsp:
                notify.warning("Vui lòng điền đầy đủ tên và đường dẫn RTSP")
            else:
                res = create_device(client, new_name.strip(), new_rtsp.strip(), new_loc.strip())
                if res and res.status_code == 200:
                    notify.success("Đăng ký thiết bị thành công")
                    st.rerun()
                else:
                    notify.error("Lỗi khi thêm thiết bị")
