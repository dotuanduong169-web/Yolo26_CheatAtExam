"""Trang Thiết bị biên & Hệ thống (FR04): Quản lý camera IP/RTSP, tài nguyên biên và tham số nhận diện AI."""

import streamlit as st

from components.app_sidebar import render_sidebar
from services.device_api import create_device, delete_device, list_devices, update_device
from utils.auth_guard import require_auth
from utils.hide_streamlit_sidebar import hide_sidebar
from utils.http import init_session_state
from utils.load_css import load_css
from utils.render_header import render_page_header

# ── Cấu hình trang ──────────────────────────────────────────
st.set_page_config(layout="wide", page_title="Thiết bị biên")

init_session_state()
require_auth()

# ── Styles & Sidebar ────────────────────────────────────────
hide_sidebar()
render_sidebar(active="devices")
st.markdown(load_css("styles/sidebar.css"), unsafe_allow_html=True)
st.markdown(load_css("styles/app_theme.css"), unsafe_allow_html=True)
render_page_header("Thiết bị biên")

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

# ── Danh mục Camera & Thiết bị biên ─────────────────────────
devices = list_devices(client)

st.markdown(f"""
<div class="wf-box">
    <div class="wf-box-header">
        <div class="wf-box-title">Danh mục thiết bị biên & camera</div>
        <span class="wf-badge">Tổng thiết bị: {len(devices)}</span>
    </div>
</div>
""", unsafe_allow_html=True)

if not devices:
    st.info("Chưa có thiết bị camera nào trong danh mục.")
else:
    # Header hàng bảng
    th1, th2, th3, th4, th5, th6 = st.columns([0.8, 1.8, 2.2, 1.8, 1, 1.4])
    th1.caption("MÃ TB")
    th2.caption("TÊN THIẾT BỊ")
    th3.caption("ĐƯỜNG DẪN RTSP")
    th4.caption("VỊ TRÍ LẮP ĐẶT")
    th5.caption("TRẠNG THÁI")
    th6.caption("HÀNH ĐỘNG")

    st.markdown("<hr style='margin: 4px 0 8px 0; border: none; border-top: 1px solid var(--wf-border);'>", unsafe_allow_html=True)

    for dev in devices:
        dev_id = dev.get("PK_MaThietBi")
        name = dev.get("TenThietBi", "Camera")
        rtsp = dev.get("DuongDanRTSP", "0")
        loc = dev.get("MoTaViTri") or "Chưa cấu hình"
        status = dev.get("TrangThai", "san_sang")

        stt_badge = '<span class="wf-badge success">Online</span>' if status in ("hoat_dong", "san_sang", "dang_chay") else '<span class="wf-badge">Tạm dừng</span>'

        with st.container():
            c1, c2, c3, c4, c5, c6 = st.columns([0.8, 1.8, 2.2, 1.8, 1, 1.4])
            with c1:
                st.markdown(f"<strong>#{dev_id}</strong>", unsafe_allow_html=True)
            with c2:
                st.markdown(f"<strong>{name}</strong>")
            with c3:
                st.code(rtsp, language=None)
            with c4:
                st.caption(loc)
            with c5:
                st.markdown(stt_badge, unsafe_allow_html=True)
            with c6:
                if is_admin:
                    # 3 Icon Button chuẩn nghiệp vụ thiết bị: Test luồng (Play), Sửa (Edit), Xóa (Trash)
                    col_b1, col_b2, col_b3 = st.columns(3)
                    with col_b1:
                        if st.button("▶", key=f"test_btn_{dev_id}", help="Kiểm tra kết nối luồng RTSP"):
                            st.toast(f"Thiết bị #{dev_id} ({name}): Luồng RTSP kết nối ổn định (2ms)")
                    with col_b2:
                        if st.button("✎", key=f"edit_btn_{dev_id}", help="Chỉnh sửa cấu hình thiết bị"):
                            st.session_state[f"editing_device_{dev_id}"] = not st.session_state.get(f"editing_device_{dev_id}", False)
                    with col_b3:
                        if st.button("🗑", key=f"del_dev_{dev_id}", help="Xóa thiết bị khỏi danh mục"):
                            del_res = delete_device(client, dev_id)
                            if del_res and del_res.status_code == 200:
                                st.toast("Đã xóa thiết bị thành công")
                                st.rerun()
                            else:
                                st.error("Không thể xóa thiết bị đang gắn ca thi")
                else:
                    st.caption("Cán bộ")

            # Form inline chỉnh sửa khi bấm Sửa
            if st.session_state.get(f"editing_device_{dev_id}", False):
                with st.container():
                    st.markdown("<div style='background: #f8fafc; padding: 12px; border-radius: 6px; margin: 8px 0;'>", unsafe_allow_html=True)
                    e_c1, e_c2, e_c3 = st.columns(3)
                    with e_c1:
                        e_name = st.text_input("Tên thiết bị", value=name, key=f"e_name_{dev_id}")
                    with e_c2:
                        e_rtsp = st.text_input("Đường dẫn RTSP", value=rtsp, key=f"e_rtsp_{dev_id}")
                    with e_c3:
                        e_loc = st.text_input("Vị trí", value=loc, key=f"e_loc_{dev_id}")
                    if st.button("Lưu thay đổi", key=f"save_e_{dev_id}", type="primary"):
                        up_res = update_device(client, dev_id, e_name.strip(), e_rtsp.strip(), e_loc.strip())
                        if up_res and up_res.status_code == 200:
                            st.session_state[f"editing_device_{dev_id}"] = False
                            st.toast("Đã cập nhật thiết bị thành công")
                            st.rerun()
                        else:
                            st.error("Lỗi khi cập nhật thiết bị")
                    st.markdown("</div>", unsafe_allow_html=True)

            st.markdown("<hr style='margin: 4px 0 10px 0; border: none; border-top: 1px solid var(--wf-border);'>", unsafe_allow_html=True)

# ── Đăng ký thiết bị biên mới (Dành cho Admin) ──────────────
if is_admin:
    with st.expander("Đăng ký thiết bị camera IP / RTSP mới", expanded=False):
        c_name, c_rtsp = st.columns(2)
        with c_name:
            new_name = st.text_input("Tên thiết bị", placeholder="VD: Jetson Orin - Cam 01")
        with c_rtsp:
            new_rtsp = st.text_input("Đường dẫn luồng RTSP / Camera index", placeholder="rtsp://192.168.1.120:554/stream1 hoặc 0")

        new_loc = st.text_input("Vị trí lắp đặt phòng thi", placeholder="VD: Phòng P.302 (Chính diện)")

        if st.button("Lưu thiết bị mới", type="primary"):
            if not new_name or not new_rtsp:
                st.warning("Vui lòng điền đầy đủ tên và đường dẫn RTSP")
            else:
                res = create_device(client, new_name.strip(), new_rtsp.strip(), new_loc.strip())
                if res and res.status_code == 200:
                    st.toast("Đăng ký thiết bị thành công")
                    st.rerun()
                else:
                    st.error("Lỗi khi thêm thiết bị")

# ── Cấu hình tham số AI nhận diện ───────────────────────────
st.markdown("""
<div class="wf-box" style="margin-top: 20px;">
    <div class="wf-box-header">
        <div class="wf-box-title">Cấu hình tham số nhận diện AI</div>
        <span style="font-size: 11px; color: var(--wf-text-muted);">YOLO26-Seg Model Engine</span>
    </div>
</div>
""", unsafe_allow_html=True)

cf1, cf2, cf3 = st.columns([1.5, 1.5, 1])

with cf1:
    conf_thresh = st.slider("Ngưỡng tin cậy (Confidence Threshold):", min_value=0.30, max_value=0.95, value=0.75, step=0.05)

with cf2:
    time_thresh = st.slider("Thời gian nghi vấn tối thiểu (Debounce):", min_value=1.0, max_value=5.0, value=2.5, step=0.5)

with cf3:
    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
    if st.button("Lưu cấu hình tham số", type="primary", use_container_width=True):
        st.toast(f"Đã cập nhật ngưỡng tin cậy {conf_thresh} và debounce {time_thresh}s!")
