"""Trang chủ: giám sát camera trực tiếp và sự kiện mới nhất."""

import time

import streamlit as st
from streamlit_autorefresh import st_autorefresh

from components.app_sidebar import render_sidebar
from config import API_BASE_URL
from services.device_api import list_devices
from services.event_api import list_session_events
from utils.auth_guard import require_auth
from utils.hide_streamlit_sidebar import hide_sidebar
from utils.http import init_session_state, safe_get, safe_post
from utils.load_css import load_css

# ── Config ──────────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="Giám sát")

CAMERA_URL = f"{API_BASE_URL}/camera"

# ── Styles ──────────────────────────────────────────────────
st.markdown(load_css("styles/sidebar.css"), unsafe_allow_html=True)
st.markdown(load_css("styles/home.css"), unsafe_allow_html=True)

# ── Session State ───────────────────────────────────────────
init_session_state()

# ── Auth ────────────────────────────────────────────────────
require_auth()

# ── Page Enter ──────────────────────────────────────────────
if st.session_state["page_loaded"] != "home":
    st.session_state["page_loaded"] = "home"
    st.session_state["refresh_key"] += 1

# ── Sync with Backend ──────────────────────────────────────
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

# ── Sidebar ─────────────────────────────────────────────────
hide_sidebar()
render_sidebar(active="home")

# ── Header ──────────────────────────────────────────────────
from utils.render_header import render_page_header
render_page_header("Giám sát thời gian thực")

# ── Device List ─────────────────────────────────────────────
devices = list_devices(st.session_state.client)

# ── Controls ────────────────────────────────────────────────
col_input, col_sub, col_cam, col_start, col_stop = st.columns([1.2, 1.2, 1.5, 1, 1])

with col_input:
    phong_thi = st.text_input("Phòng thi", placeholder="VD: P101", label_visibility="collapsed")

with col_sub:
    mon_thi = st.text_input("Môn thi", placeholder="VD: Toán", label_visibility="collapsed")

with col_cam:
    if devices:
        selected = st.selectbox(
            "Chọn thiết bị", devices,
            format_func=lambda x: f"{x.get('TenThietBi')} ({x.get('MoTaViTri') or '—'})",
            label_visibility="collapsed",
        )
        device_id = selected["PK_MaThietBi"]
    else:
        st.warning("Chưa có thiết bị (vào trang Thiết bị)")
        device_id = None

with col_start:
    if not st.session_state["running"]:
        disabled = not (phong_thi or "").strip() or device_id is None
        if st.button("▷ Bắt đầu phân tích", use_container_width=True, disabled=disabled, type="primary"):
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

# ── Main Layout ─────────────────────────────────────────────
left_col, right_col = st.columns([2.5, 1.5])

# Left panel — camera feed
with left_col:
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
        start_time = st.session_state["capture_start_time"]
        elapsed_str = "00:00:00"
        if start_time:
            elapsed = int(time.time() - start_time)
            h, m, s = elapsed // 3600, (elapsed % 3600) // 60, elapsed % 60
            elapsed_str = f"{h:02d}:{m:02d}:{s:02d}"

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

        if start_time:
            elapsed_total = time.time() - start_time
            cycle_offset = elapsed_total % 30
            st.markdown(f"""
            <div class="capture-countdown">
                <div class="countdown-header">
                    <span class="countdown-label">🔄 Đang trích xuất sự kiện...</span>
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

# Right panel — latest events
with right_col:
    st.markdown("""
    <div class="section-header">
        <h3>🚨 Sự kiện gian lận</h3>
        <span class="refresh-label">Mới nhất</span>
    </div>
    """, unsafe_allow_html=True)

    if st.session_state["running"] and st.session_state["session_id"]:
        sid = st.session_state["session_id"]
        events = list_session_events(st.session_state.client, sid, limit=10)

        if not events:
            st.info("Chưa ghi nhận gian lận")
        else:
            box = st.container(height=500, border=False)
            with box:
                for ev in events:
                    label = ev.get("LoaiHanhVi", "?")
                    conf = round(float(ev.get("DoTinCay", 0)) * 100, 1)
                    stt = ev.get("TrangThaiKiemTra", "cho_kiem_tra")
                    st.markdown('<div class="frame-item">', unsafe_allow_html=True)
                    fc1, fc2 = st.columns([2, 1])
                    with fc1:
                        st.caption(f"{label} · {conf}% · {stt}")
                        st.caption(str(ev.get("ThoiGianPhatHien", ""))[:19])
                    with fc2:
                        if st.button(
                            "XEM",
                            key=f"ev_{ev['PK_MaSuKien']}",
                            use_container_width=True,
                        ):
                            st.session_state["event_id"] = ev["PK_MaSuKien"]
                            st.switch_page("pages/event_detail.py")
                    st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("Chưa bắt đầu phiên giám sát")

    if st.session_state["running"]:
        st.markdown('<div class="view-all-btn">', unsafe_allow_html=True)
        if st.button("📊 XEM TẤT CẢ", use_container_width=True):
            st.switch_page("pages/events.py")
        st.markdown("</div>", unsafe_allow_html=True)

# ── Auto Refresh ────────────────────────────────────────────
if st.session_state["running"]:
    st_autorefresh(
        interval=10000,
        key=f"refresh_{st.session_state['refresh_key']}",
    )
