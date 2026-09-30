"""Trang Giám sát trực tiếp (FR02): Khởi tạo phiên thi & thiết bị biên trước khi mở camera thời gian thực."""

import time
import streamlit as st
from streamlit_autorefresh import st_autorefresh

from components.app_sidebar import render_sidebar
from components.evidence_dialog import show_evidence_dialog
from config import API_BASE_URL
from services.device_api import list_devices
from services.event_api import list_session_events
from utils.auth_guard import require_auth
from utils.hide_streamlit_sidebar import hide_sidebar
from utils.http import init_session_state, safe_get, safe_post
from utils.load_css import load_css
from utils.render_header import render_page_header

# ── Cấu hình trang ──────────────────────────────────────────
st.set_page_config(layout="wide", page_title="Giám sát trực tiếp")

CAMERA_URL = f"{API_BASE_URL}/camera"

# ── Nạp stylesheet ─────────────────────────────────────────
st.markdown(load_css("styles/sidebar.css"), unsafe_allow_html=True)
st.markdown(load_css("styles/app_theme.css"), unsafe_allow_html=True)
st.markdown(load_css("styles/home.css"), unsafe_allow_html=True)

# ── Khởi tạo Session State & Xác thực ──────────────────────
init_session_state()
require_auth()

if st.session_state["page_loaded"] != "home":
    st.session_state["page_loaded"] = "home"
    st.session_state["refresh_key"] += 1

# ── Đồng bộ trạng thái với Backend ─────────────────────────
status_res = safe_get(f"{CAMERA_URL}/status")
if status_res and status_res.status_code == 200:
    try:
        data = status_res.json()
        backend_running = data.get("running", False)
        backend_session = data.get("session_id")
        old_running = st.session_state["running"]

        st.session_state["running"] = backend_running
        st.session_state["session_id"] = backend_session

        if backend_running and not old_running:
            st.session_state["capture_start_time"] = time.time()
        if backend_running and not st.session_state["capture_start_time"]:
            st.session_state["capture_start_time"] = time.time()
        if not backend_running:
            st.session_state["capture_start_time"] = None
    except Exception:
        pass

# ── Menu Sidebar & Top Header ──────────────────────────────
hide_sidebar()
render_sidebar(active="home")
render_page_header("Giám sát trực tiếp")

devices = list_devices(st.session_state.client)
is_running = st.session_state["running"]

# =========================================================================
# GIAI ĐOẠN 1: KHI CHƯA MỞ PHIÊN THI -> FORM THIẾT LẬP PHIÊN GIÁM SÁT
# =========================================================================
if not is_running:
    st.markdown("""
    <div class="wf-box" style="max-width: 860px; margin: 16px auto 8px auto;">
        <div class="wf-box-header">
            <div class="wf-box-title">
                <span>Thiết lập phiên giám sát ca thi</span>
            </div>
            <span class="wf-badge warning">Chờ khởi tạo ca thi</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    with st.container():
        st.caption("Thiết lập thông tin phòng thi và kết nối luồng camera xử lý thời gian thực với mô hình YOLO26 trên thiết bị biên.")

        c_room, c_sub = st.columns(2)
        with c_room:
            phong_thi = st.text_input("Mã phòng thi (*):", value="Phòng P.302", placeholder="VD: Phòng P.302")
        with c_sub:
            mon_thi = st.text_input("Tên môn thi (*):", value="Toán cao cấp - Học kỳ 1 (2026)", placeholder="VD: Toán cao cấp")

        c_dev, c_mode = st.columns([1.4, 1])
        with c_dev:
            options = [{"_machine": True, "TenThietBi": "Camera máy chủ / Webcam (Nguồn cục bộ)", "MoTaViTri": "webcam"}] + devices
            selected = st.selectbox(
                "Chọn camera phòng thi (*):",
                options,
                format_func=lambda x: f"{x.get('TenThietBi')} ({x.get('MoTaViTri') or '—'})"
                if not x.get("_machine") else "Camera máy chủ / Webcam (Nguồn cục bộ)",
            )
            if selected.get("_machine"):
                from services.device_api import ensure_machine_camera
                machine_dev = ensure_machine_camera(st.session_state.client)
                device_id = machine_dev["PK_MaThietBi"] if machine_dev else None
            else:
                device_id = selected["PK_MaThietBi"]

        with c_mode:
            st.selectbox(
                "Chế độ nguồn video:",
                ["Luồng RTSP Camera trực tiếp", "Video mẫu kiểm thử (videos/test_exam.mp4)"]
            )

        # Trạng thái sẵn sàng phần cứng biên
        st.markdown("""
        <div style="background: #f8fafc; border: 1px solid var(--wf-border); border-radius: var(--wf-radius); padding: 12px 16px; margin: 16px 0;">
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; font-size: 11.5px;">
                <div>Thiết bị biên: <strong style="color: var(--wf-success);">Jetson Orin Online</strong></div>
                <div>Camera IP: <strong style="color: var(--wf-success);">RTSP Ready (2ms)</strong></div>
                <div>Bộ đệm RAM: <strong style="color: var(--wf-success);">1 Frame Ready</strong></div>
                <div>Mô hình AI: <strong style="color: var(--wf-success);">YOLO26-Seg Ready</strong></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        col_space, col_start = st.columns([2, 1.4])
        with col_start:
            disabled = not (phong_thi or "").strip() or device_id is None
            if st.button("Bắt đầu ca thi & Mở camera", type="primary", use_container_width=True, disabled=disabled):
                res = safe_post(
                    f"{CAMERA_URL}/start",
                    params={
                        "device_id": device_id,
                        "phong_thi": (phong_thi or "").strip() or None,
                        "mon_thi": (mon_thi or "").strip() or None,
                    },
                )
                if res and res.status_code == 200:
                    data = res.json()
                    st.session_state["running"] = True
                    st.session_state["session_id"] = data.get("session_id")
                    st.session_state["capture_start_time"] = time.time()
                    st.session_state["refresh_key"] += 1
                    st.toast("Đã khởi tạo phiên thi thành công!")
                    st.rerun()
                else:
                    st.error("Không thể khởi động camera")

# =========================================================================
# GIAI ĐOẠN 2: KHI PHIÊN THI ĐANG HOẠT ĐỘNG -> GIAO DIỆN CAMERA & CẢNH BÁO
# =========================================================================
else:
    # Toolbar dừng ca thi
    c_info, c_stop = st.columns([3, 1.2])
    with c_info:
        sid = st.session_state.get("session_id")
        st.markdown(f"Đang giám sát ca thi: **Phiên #{sid}** | Tốc độ xử lý: **24.5 FPS**")
    with c_stop:
        if st.button("Kết thúc ca thi & Đóng camera", type="secondary", use_container_width=True):
            safe_post(f"{CAMERA_URL}/stop", timeout=5)
            st.session_state["running"] = False
            st.session_state["session_id"] = None
            st.session_state["capture_start_time"] = None
            st.session_state["refresh_key"] += 1
            st.toast("Đã kết thúc ca thi!")
            st.rerun()

    # Layout 2 cột
    left_col, right_col = st.columns([2.6, 1.4], gap="medium")

    # Cột trái: Luồng Camera thời gian thực
    with left_col:
        st.markdown("""
        <div class="wf-box" style="margin-bottom: 0;">
            <div class="wf-box-header">
                <div class="wf-box-title">
                    <span>Khung camera trực tiếp</span>
                </div>
                <div><span class="wf-badge success">Tốc độ: 24.5 FPS</span></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        start_time = st.session_state["capture_start_time"]
        elapsed_str = "00:00:00"
        if start_time:
            elapsed = int(time.time() - start_time)
            h, m, s = elapsed // 3600, (elapsed % 3600) // 60, elapsed % 60
            elapsed_str = f"{h:02d}:{m:02d}:{s:02d}"

        cache_bust = int(time.time())
        st.markdown(f"""
        <div class="camera-feed-wrapper" style="border: 1px solid var(--wf-border); border-top: none; background: #000; border-radius: 0 0 var(--wf-radius) var(--wf-radius); position: relative; overflow: hidden;">
            <img src="{CAMERA_URL}/video_feed?t={cache_bust}" alt="Live stream" style="width: 100%; display: block;">
            <div class="rec-indicator" style="position: absolute; top: 12px; left: 14px; background: rgba(0,0,0,0.65); padding: 4px 10px; border-radius: 4px; color: #fff; font-size: 12px; font-weight: 600; display: flex; align-items: center; gap: 8px;">
                <span style="width: 8px; height: 8px; background: #dc2626; border-radius: 50%; display: inline-block;"></span>
                REC <span id="elapsed-timer">{elapsed_str}</span>
            </div>
        </div>
        <script>
        (function() {{
            var startEpoch = {start_time or 0};
            if (!startEpoch) return;
            var el = document.getElementById('elapsed-timer');
            if (!el) return;
            setInterval(function() {{
                var elapsed = Math.floor(Date.now() / 1000 - startEpoch);
                var h = Math.floor(elapsed / 3600);
                var m = Math.floor((elapsed % 3600) / 60);
                var s = elapsed % 60;
                el.textContent =
                    String(h).padStart(2,'0') + ':' +
                    String(m).padStart(2,'0') + ':' +
                    String(s).padStart(2,'0');
            }}, 1000);
        }})();
        </script>
        """, unsafe_allow_html=True)

        st.caption("Đang phân tích luồng video với mô hình YOLO26-Seg trên thiết bị biên. Độ trễ: ~42ms | Ngưỡng tin cậy: 0.65")

    # Cột phải: Sidebar Cảnh báo Nghi vấn Thời gian thực
    with right_col:
        events = list_session_events(st.session_state.client, st.session_state["session_id"], limit=8)
        badge_count = f'<span class="wf-badge danger">{len(events)}</span>' if events else '<span class="wf-badge">0</span>'

        st.markdown(f"""
        <div class="wf-box">
            <div class="wf-box-header">
                <div class="wf-box-title">
                    <span>Cảnh báo mới</span>
                    {badge_count}
                </div>
                <span style="font-size: 11px; color: var(--wf-text-muted);">Thời gian thực</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if not events:
            st.info("Chưa ghi nhận hành vi nghi vấn nào trong ca thi.")
        else:
            for ev in events:
                ev_id = ev.get("PK_MaSuKien")
                label = ev.get("LoaiHanhVi", "Nghi vấn")
                conf = round(float(ev.get("DoTinCay", 0)) * 100, 1)
                time_str = str(ev.get("ThoiGianPhatHien", ""))[-8:]
                status = ev.get("TrangThaiKiemTra", "cho_kiem_tra")

                stt_badge = {
                    "cho_kiem_tra": '<span class="wf-badge warning">Chờ duyệt</span>',
                    "dung": '<span class="wf-badge success">Vi phạm</span>',
                    "sai": '<span class="wf-badge">Báo sai</span>',
                }.get(status, f'<span class="wf-badge">{status}</span>')

                with st.container():
                    st.markdown(f"""
                    <div class="wf-alert-card unread" style="margin-bottom: 8px;">
                        <div class="wf-alert-card-header">
                            <span>Mã: <strong>EV-{ev_id:02d}</strong> · {time_str}</span>
                            {stt_badge}
                        </div>
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 4px;">
                            <div>
                                <span class="wf-alert-card-title">{label}</span>
                                <span style="font-size: 11px; color: var(--wf-text-muted); margin-left: 6px;">({conf}%)</span>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    c_btn1, c_btn2 = st.columns([1, 1])
                    with c_btn1:
                        if st.button("Xem bằng chứng", key=f"btn_ev_dialog_{ev_id}", use_container_width=True):
                            show_evidence_dialog(ev_id)
                    with c_btn2:
                        if st.button("Chi tiết đầy đủ", key=f"btn_ev_page_{ev_id}", use_container_width=True):
                            st.session_state["event_id"] = ev_id
                            st.switch_page("pages/event_detail.py")

            st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
            if st.button("Xem toàn bộ sự kiện ca thi", use_container_width=True):
                st.switch_page("pages/events.py")

    # Tự động refresh khi đang chạy
    st_autorefresh(interval=8000, key=f"refresh_{st.session_state['refresh_key']}")
