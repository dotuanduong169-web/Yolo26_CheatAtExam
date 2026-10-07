"""Trang Thiết bị biên & Hệ thống (FR04): Quản lý camera IP/RTSP và tài nguyên biên."""

import math

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

# ── 3 Khung tổng quan thực tế từ API ───────────────────────
from config import API_BASE_URL
from utils.http import safe_get

_devices_all = list_devices(st.session_state.client)
_n_total = len(_devices_all)
_n_ready = sum(1 for d in _devices_all if (d.get("TrangThai") or "") == "san_sang")
_cam_res = safe_get(f"{API_BASE_URL}/camera/status")
_cam_data = _cam_res.json() if (_cam_res and _cam_res.status_code == 200) else {}
_is_running = bool(_cam_data.get("running"))
_fps_val = _cam_data.get("fps")

if _is_running:
    if _fps_val is not None and _fps_val > 0:
        _live_txt = f"{_fps_val:.1f} FPS"
        _live_hint = "Camera AI đang hoạt động thời gian thực"
    else:
        _live_txt = "Đang chạy"
        _live_hint = "Luồng camera đang mở"
else:
    _live_txt = "Đang dừng"
    _live_hint = "Chưa mở luồng camera"

st.markdown(f"""
<div class="wf-grid-3">
    <div class="wf-stat-tile">
        <div class="wf-stat-label">Tổng thiết bị biên</div>
        <div class="wf-stat-num">{_n_total}</div>
        <div class="wf-stat-hint">Đã đăng ký trong hệ thống</div>
    </div>
    <div class="wf-stat-tile">
        <div class="wf-stat-label">Thiết bị sẵn sàng</div>
        <div class="wf-stat-num">{_n_ready}</div>
        <div class="wf-stat-hint">Trạng thái san_sang, chờ mở phiên</div>
    </div>
    <div class="wf-stat-tile">
        <div class="wf-stat-label">Tốc độ xử lý / Luồng giám sát</div>
        <div class="wf-stat-num" style="font-size:22px;">{_live_txt}</div>
        <div class="wf-stat-hint">{_live_hint}</div>
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

    msg_slot = st.empty()
    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Hủy bỏ", use_container_width=True):
            st.rerun()
    with c2:
        if st.button("Lưu thiết bị mới", type="primary", use_container_width=True):
            if not new_name.strip() or not new_rtsp.strip():
                with msg_slot:
                    notify.inline_warning("Vui lòng điền đầy đủ tên thiết bị và đường dẫn RTSP")
            else:
                res = create_device(client, new_name.strip(), new_rtsp.strip(), new_loc.strip())
                if res and res.status_code == 200:
                    notify.defer_success("Đăng ký thiết bị thành công")
                    st.rerun()
                else:
                    with msg_slot:
                        notify.inline_error("Lỗi khi thêm thiết bị")


@st.dialog("Chỉnh sửa thông tin thiết bị")
def edit_device_dialog(dev_id: int, cur_name: str, cur_rtsp: str, cur_loc: str):
    e_name = st.text_input("Tên thiết bị", value=cur_name)
    e_rtsp = st.text_input("Đường dẫn RTSP", value=cur_rtsp)
    e_loc = st.text_input("Vị trí lắp đặt", value=cur_loc)

    msg_slot = st.empty()
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
                notify.defer_success("Đã cập nhật thiết bị thành công")
                st.rerun()
            else:
                with msg_slot:
                    notify.inline_error("Lỗi khi cập nhật thiết bị")


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
                notify.defer_success(f"Đã xóa thiết bị #{dev_id} thành công!")
                st.rerun()
            elif del_res is not None and del_res.status_code == 400:
                notify.inline_error("Không thể xóa thiết bị đang gắn ca thi hoặc có phiên giám sát.")
            else:
                err_text = del_res.text if del_res else "Lỗi kết nối máy chủ"
                notify.inline_error(f"Xóa thiết bị thất bại: {err_text}")


# ── Xử lý query params thao tác thiết bị (từ link icon SVG) ──
if "test_dev" in st.query_params:
    try:
        t_id = int(st.query_params["test_dev"])
        del st.query_params["test_dev"]
        test_res = test_device(client, t_id)
        if test_res.get("online"):
            lat = test_res.get("latency_ms", 5)
            notify.success(f"Thiết bị #{t_id}: {test_res.get('message')} ({lat}ms)")
        else:
            notify.error(f"Thiết bị #{t_id}: {test_res.get('message')}")
    except Exception:
        pass

# ── Danh mục Camera & Thiết bị biên ─────────────────────────
devices = list_devices(client)

if "edit_dev" in st.query_params:
    try:
        e_id = int(st.query_params["edit_dev"])
        del st.query_params["edit_dev"]
        matched_dev = next((d for d in devices if d.get("PK_MaThietBi") == e_id), None)
        if matched_dev:
            edit_device_dialog(
                e_id,
                matched_dev.get("TenThietBi", ""),
                matched_dev.get("DuongDanRTSP", ""),
                matched_dev.get("MoTaViTri", ""),
            )
    except Exception:
        pass

if "del_dev" in st.query_params:
    try:
        d_id = int(st.query_params["del_dev"])
        del st.query_params["del_dev"]
        matched_dev = next((d for d in devices if d.get("PK_MaThietBi") == d_id), None)
        d_name = matched_dev.get("TenThietBi", f"Thiết bị #{d_id}") if matched_dev else f"Thiết bị #{d_id}"
        delete_device_dialog(d_id, d_name)
    except Exception:
        pass

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
    # Phân trang thiết bị (10 thiết bị / trang)
    PAGE_SIZE = 10
    total_devices_count = len(devices)
    st.session_state.setdefault("dev_page", 1)
    total_dev_pages = max(1, math.ceil(total_devices_count / PAGE_SIZE))
    st.session_state.dev_page = min(st.session_state.dev_page, total_dev_pages)
    current_dev_page = st.session_state.dev_page

    dev_start_idx = (current_dev_page - 1) * PAGE_SIZE
    dev_end_idx = min(dev_start_idx + PAGE_SIZE, total_devices_count)
    page_devices = devices[dev_start_idx:dev_end_idx]

    # Header hàng bảng
    th1, th2, th3, th4, th5, th6 = st.columns([0.8, 1.8, 2.5, 1.6, 1.0, 1.1])
    th1.caption("MÃ TB")
    th2.caption("TÊN THIẾT BỊ")
    th3.caption("ĐƯỜNG DẪN RTSP")
    th4.caption("VỊ TRÍ LẮP ĐẶT")
    th5.caption("TRẠNG THÁI")
    th6.markdown('<div style="text-align:right; font-size:11.5px; font-weight:700; color:#64748b; letter-spacing:0.5px;">THAO TÁC</div>', unsafe_allow_html=True)

    st.markdown("<hr style='margin: 4px 0 8px 0; border: none; border-top: 1px solid var(--wf-border);'>", unsafe_allow_html=True)

    for dev in page_devices:
        dev_id = dev.get("PK_MaThietBi")
        name = dev.get("TenThietBi", "Camera")
        rtsp = dev.get("DuongDanRTSP", "0")
        loc = dev.get("MoTaViTri") or "Chưa cấu hình"
        status = dev.get("TrangThai", "san_sang")
        stt_badge = get_device_status_badge(status)

        with st.container():
            c1, c2, c3, c4, c5, c6 = st.columns([0.8, 1.8, 2.5, 1.6, 1.0, 1.1])
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
                    # Nút native (icon CSS btn_act_*) → dialog/API trực tiếp,
                    # không qua URL nên không reload/chớp (giao diện giữ nguyên)
                    db1, db2, db3 = st.columns(3, gap="small")
                    with db1:
                        if st.button("Test", key=f"btn_act_test_dev_{dev_id}", help="Kiểm tra kết nối camera RTSP"):
                            test_res = test_device(client, dev_id)
                            if test_res.get("online"):
                                lat = test_res.get("latency_ms", 5)
                                notify.success(f"Thiết bị #{dev_id}: {test_res.get('message')} ({lat}ms)")
                            else:
                                notify.error(f"Thiết bị #{dev_id}: {test_res.get('message')}")
                    with db2:
                        if st.button("Sửa", key=f"btn_act_edit_dev_{dev_id}", help="Chỉnh sửa thông tin thiết bị"):
                            edit_device_dialog(
                                dev_id,
                                dev.get("TenThietBi", ""),
                                dev.get("DuongDanRTSP", ""),
                                dev.get("MoTaViTri", ""),
                            )
                    with db3:
                        if st.button("Xóa", key=f"btn_act_del_dev_{dev_id}", help="Xóa thiết bị khỏi danh mục"):
                            delete_device_dialog(dev_id, dev.get("TenThietBi", f"Thiết bị #{dev_id}"))
                else:
                    st.caption("Cán bộ")

            st.markdown("<hr style='margin: 4px 0 10px 0; border: none; border-top: 1px solid var(--wf-border);'>", unsafe_allow_html=True)

    # Phân trang thiết bị chuẩn Figma Standard
    st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)
    dev_pg_left, dev_pg_right = st.columns([3, 1])
    with dev_pg_left:
        st.markdown(
            f"<div style='font-size: 13px; color: #64748b; line-height: 32px; font-weight: 500;'>"
            f"Hiển thị <strong>{dev_start_idx + 1 if total_devices_count > 0 else 0} – {dev_end_idx}</strong> trong tổng số <strong>{total_devices_count}</strong> thiết bị"
            f"</div>",
            unsafe_allow_html=True,
        )

    with dev_pg_right:
        _dev_pages: list = []
        for p in range(1, total_dev_pages + 1):
            if total_dev_pages > 7 and abs(p - current_dev_page) > 2 and p != 1 and p != total_dev_pages:
                if p == 2 or p == total_dev_pages - 1:
                    _dev_pages.append(None)
                continue
            _dev_pages.append(p)
        _dcols = st.columns(len(_dev_pages) + 2, gap="small")
        with _dcols[0]:
            if st.button("‹", key="pag_btn_dev_prev", disabled=(current_dev_page <= 1)):
                st.session_state.dev_page = current_dev_page - 1
                st.rerun()
        for _i, _p in enumerate(_dev_pages):
            with _dcols[_i + 1]:
                if _p is None:
                    st.markdown("<div style='display:flex;align-items:center;justify-content:center;height:32px;color:#94a3b8;'>…</div>", unsafe_allow_html=True)
                elif _p == current_dev_page:
                    st.button(str(_p), key=f"pag_btn_dev_cur_{_p}", type="primary", disabled=True)
                elif st.button(str(_p), key=f"pag_btn_dev_{_p}"):
                    st.session_state.dev_page = _p
                    st.rerun()
        with _dcols[-1]:
            if st.button("›", key="pag_btn_dev_next", disabled=(current_dev_page >= total_dev_pages)):
                st.session_state.dev_page = current_dev_page + 1
                st.rerun()

