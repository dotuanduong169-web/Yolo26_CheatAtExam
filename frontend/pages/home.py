"""Trang giám sát camera trực tiếp và khung hình trích xuất.
Luồng chính: đồng bộ trạng thái /camera/status -> điều khiển bắt đầu/dừng -> hiện luồng MJPEG -> liệt kê khung hình."""

import time

import streamlit as st
from streamlit_autorefresh import st_autorefresh

from components.app_sidebar import render_sidebar
from config import API_BASE_URL
from services.frame_api import get_frames_by_session
from utils.auth_guard import require_auth
from utils.hide_streamlit_sidebar import hide_sidebar
from utils.http import init_session_state, safe_get, safe_post
from utils.load_css import load_css

# ── Cấu hình trang ────────────────────────────────────────
st.set_page_config(layout="wide", page_title="Giám sát")

CAMERA_URL = f"{API_BASE_URL}/camera"

# ── Nạp CSS ───────────────────────────────────────────────
st.markdown(load_css("styles/sidebar.css"), unsafe_allow_html=True)
st.markdown(load_css("styles/home.css"), unsafe_allow_html=True)

# ── Khởi tạo session ──────────────────────────────────────
init_session_state()

# ── Chặn trang khi chưa đăng nhập ─────────────────────────
require_auth()

# ── Đánh dấu lần vào trang để tránh chạy lại ──────────────
if st.session_state["page_loaded"] != "home":
    st.session_state["page_loaded"] = "home"
    st.session_state["refresh_key"] += 1

# ── Đồng bộ trạng thái chạy với backend ───────────────────
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

# ── Thanh bên ─────────────────────────────────────────────
hide_sidebar()
render_sidebar(active="home")

# ── Tiêu đề trang ─────────────────────────────────────────
from utils.render_header import render_page_header
render_page_header("Giám sát thời gian thực")

# ── Danh sách camera khả dụng ─────────────────────────────
cams = []
cams_res = safe_get(f"{CAMERA_URL}/list")

if cams_res:
    if cams_res.status_code == 200:
        cams = cams_res.json().get("cameras", [])
    elif cams_res.status_code == 401:
        st.error("Phiên đăng nhập hết hạn")
        if st.button("Đăng nhập lại"):
            st.session_state.clear()
            st.switch_page("pages/login.py")
        st.stop()

# ── Cụm điều khiển mã lớp và camera ───────────────────────
col_input, col_cam, col_start, col_stop = st.columns([1.5, 1.5, 1, 1])

with col_input:
    class_id = st.text_input("Nhập mã lớp", placeholder="VD: 10A1", label_visibility="collapsed")

with col_cam:
    if cams:
        selected_cam = st.selectbox(
            "Chọn camera", cams,
            format_func=lambda x: x.get("name", "Unknown"),
            label_visibility="collapsed",
        )
        camera_index = selected_cam["index"]
    else:
        st.warning("Không có camera")
        camera_index = None

with col_start:
    if not st.session_state["running"]:
        disabled = not class_id.strip() or camera_index is None
        if st.button("▷ Bắt đầu phân tích", use_container_width=True, disabled=disabled, type="primary"):
            res = safe_post(
                f"{CAMERA_URL}/start",
                params={"camera_index": camera_index, "class_id": class_id.strip()},
            )
            if res and res.status_code == 200:
                data = res.json()
                st.session_state["running"] = True
                st.session_state["session_id"] = data.get("session_id")
                st.session_state["capture_start_time"] = time.time()
                st.session_state["refresh_key"] += 1
                st.rerun()
            else:
                st.error("Không thể bắt đầu camera")

with col_stop:
    if st.session_state["running"]:
        if st.button("□ Dừng phân tích", use_container_width=True, type="secondary"):
            safe_post(f"{CAMERA_URL}/stop", timeout=5)
            st.session_state["running"] = False
            st.session_state["session_id"] = None
            st.session_state["capture_start_time"] = None
            st.session_state["refresh_key"] += 1
            st.rerun()

# ── Bố cục chính 2 cột ────────────────────────────────────
left_col, right_col = st.columns([2.5, 1.5])

# Cột trái — luồng camera trực tiếp
with left_col:

    # Tiêu đề khối kèm trạng thái camera
    is_running = st.session_state["running"]
    status_class = "active" if is_running else "inactive"
    status_text = "Đang phát" if is_running else "Chờ kết nối"
    st.markdown(f"""
    <div class="section-header">
        <h3>📹 Camera trực tiếp</h3>
        <span class="status-badge {status_class}">● {status_text}</span>
    </div>
    """, unsafe_allow_html=True)

    if is_running:
        # Đồng hồ đã quay — tính phía client bằng JS cho mượt
        # để không phải chạy lại toàn trang Streamlit
        start_time = st.session_state["capture_start_time"]
        elapsed_str = "00:00:00"
        if start_time:
            elapsed = int(time.time() - start_time)
            h, m, s = elapsed // 3600, (elapsed % 3600) // 60, elapsed % 60
            elapsed_str = f"{h:02d}:{m:02d}:{s:02d}"

        # Thêm tham số thời gian để trình duyệt không dùng lại
        # kết nối MJPEG cũ đã ngắt khi trang chạy lại.
        cache_bust = int(time.time())
        st.markdown(f"""
        <div class="camera-feed-wrapper">
            <img src="{CAMERA_URL}/video_feed?t={cache_bust}" alt="Camera feed">
            <div class="rec-indicator">
                <span class="rec-dot"></span>
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

        # Đếm ngược chụp khung hình — chạy hoàn toàn phía client bằng CSS + JS
        # nên vẫn mượt dù Streamlit có chạy lại theo chu kỳ
        if start_time:
            elapsed_total = time.time() - start_time
            cycle_offset = elapsed_total % 30
            st.markdown(f"""
            <div class="capture-countdown">
                <div class="countdown-header">
                    <span class="countdown-label">🔄 Đang trích xuất khung hình...</span>
                    <span class="countdown-timer">Mỗi 30 giây</span>
                </div>
                <div class="countdown-track">
                    <div class="countdown-fill" id="countdown-bar"
                         style="--offset: {cycle_offset}s"></div>
                </div>
            </div>
            <script>
            (function() {{
                var startEpoch = {start_time};
                var bar = document.getElementById('countdown-bar');
                if (!bar) return;
                function update() {{
                    var elapsed = (Date.now() / 1000 - startEpoch) % 30;
                    var pct = (elapsed / 30) * 100;
                    bar.style.width = pct + '%';
                }}
                update();
                setInterval(update, 500);
            }})();
            </script>
            """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="camera-placeholder">
            <span class="icon">📷</span>
            <span class="text">Nhấn "Bắt đầu phân tích" để mở camera</span>
        </div>
        """, unsafe_allow_html=True)

    # Kết thúc cột trái

# Cột phải — khung hình đã trích xuất
with right_col:

    st.markdown("""
    <div class="section-header">
        <h3>🖼 Khung hình trích xuất</h3>
        <span class="refresh-label">Mỗi 30s</span>
    </div>
    """, unsafe_allow_html=True)

    if st.session_state["running"] and st.session_state["session_id"]:
        sid = st.session_state["session_id"]
        frames = get_frames_by_session(st.session_state.client, sid)

        if not frames:
            st.info("Chưa có khung hình nào được trích xuất")
        else:
            box = st.container(height=500, border=False)
            with box:
                for frame in frames:
                    img_path = frame.get("image_path")
                    if not img_path:
                        continue

                    st.markdown('<div class="frame-item">', unsafe_allow_html=True)
                    st.image(img_path, use_container_width=True)

                    fc1, fc2 = st.columns([2, 1])
                    with fc1:
                        st.caption(f"Nhận diện: {frame.get('total_students', '?')} HS")
                        st.caption(frame.get("extracted_at", ""))
                    with fc2:
                        if st.button(
                            "XEM CHI TIẾT",
                            key=f"detail_{frame['frame_id']}",
                            use_container_width=True,
                        ):
                            st.session_state["frame_id"] = frame["frame_id"]
                            st.switch_page("pages/frame_detail.py")

                    st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("Chưa bắt đầu phiên giám sát")


    if st.session_state["running"]:
        st.markdown('<div class="view-all-btn">', unsafe_allow_html=True)
        if st.button("📊 XEM TẤT CẢ", use_container_width=True):
            st.switch_page("pages/session_analysis.py")
        st.markdown("</div>", unsafe_allow_html=True)

    # Kết thúc cột phải

# ── Tự động làm mới ───────────────────────────────────────
# Làm mới mỗi 10 giây (không phải 1 giây!) — thẻ <img> MJPEG tự cập nhật
# độc lập; Streamlit chỉ cần chạy lại để nạp danh sách khung hình
# và đồng bộ trạng thái backend. Chạy lại mỗi 1 giây gây xung đột click
# nút và gọi API dư thừa.
if st.session_state["running"]:
    st_autorefresh(
        interval=10000,
        key=f"refresh_{st.session_state['refresh_key']}",
    )