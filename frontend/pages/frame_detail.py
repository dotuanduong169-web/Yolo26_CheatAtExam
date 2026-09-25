"""Trang chi tiết khung hình: xem ảnh và sửa nhãn từng học sinh.
Luồng chính: tải chi tiết frame -> phủ hộp bbox theo % -> nhấn bbox đổi nhãn Cheat_Paper/Answer_paper -> đồng bộ bảng bên dưới."""

import base64

import streamlit as st
from PIL import Image

from components.app_sidebar import render_sidebar
from config import API_BASE_URL
from services.frame_api import get_frame_detail
from utils.auth_guard import require_auth
from utils.hide_streamlit_sidebar import hide_sidebar
from utils.http import init_session_state
from utils.load_css import load_css
from utils.render_header import render_page_header

# ── Cấu hình trang ────────────────────────────────────────
st.set_page_config(layout="wide", page_title="Chi tiết khung hình")

init_session_state()
require_auth()

# ── Thanh bên và CSS ──────────────────────────────────────
hide_sidebar()
render_sidebar(active="home")
st.markdown(load_css("styles/sidebar.css"), unsafe_allow_html=True)
st.markdown(load_css("styles/frame_detail.css"), unsafe_allow_html=True)

# ── Lấy mã khung hình cần xem ─────────────────────────────
frame_id = st.session_state.get("frame_id")
if not frame_id:
    st.warning("Không có frame để xem.")
    st.stop()


# ── Tải dữ liệu khung hình ─────────────────────────────────
data = get_frame_detail(st.session_state.client, frame_id)
if not data:
    st.error("Không lấy được dữ liệu frame.")
    st.stop()

total = data.get("total_students", 0)
sleeping = data.get("sleeping_count", 0)
focus = data.get("focus_count", 0)
conf = round(data.get("avg_confidence", 0) * 100, 1)

# Tỷ lệ phần trăm cho biểu đồ phân bổ
focus_pct = round(focus / total * 100) if total else 0
sleeping_pct = round(sleeping / total * 100) if total else 0
# Hiệu chỉnh để tổng đúng 100% khi chỉ có hai nhóm
if total and (focus + sleeping == total):
    sleeping_pct = 100 - focus_pct

detections = data.get("detections", [])

# ── Tiêu đề trang ─────────────────────────────────────────
render_page_header(f"Chi tiết khung hình #{frame_id}")

# ── Điều hướng quay lại: về trang phân tích nếu là phiên đang chạy, ngược lại về chi tiết phiên
active_session_id = st.session_state.get("session_id")
is_running = st.session_state.get("running", False)
frame_session_id = data.get("session_id")

# So sánh được cả khi kiểu dữ liệu khác nhau (số và chuỗi)
try:
    match = int(active_session_id or 0) == int(frame_session_id or 0)
except (ValueError, TypeError):
    match = False

is_active_frame = is_running and match
back_label = "← Quay lại Giám sát" if is_active_frame else "← Quay lại Chi tiết phiên"

if st.button(back_label):
    if is_active_frame:
        st.switch_page("pages/session_analysis.py")
    else:
        # Gán ngữ cảnh phiên cho trang chi tiết lịch sử
        if frame_session_id:
            st.session_state["selected_session"] = frame_session_id
        st.switch_page("pages/session_detail.py")

# ── Bố cục chính 2 cột ────────────────────────────────────
left_col, right_col = st.columns([1.6, 1], gap="medium")

# ── TRÁI: ảnh tương tác đổi nhãn ──────────────────────────
with left_col:
    st.markdown(f"""
    <div class="img-card">
        <div class="img-card-header">
            <span class="cam-label">
                <span class="icon">📹</span>
                Camera Phòng Học 01 - Khung hình #{frame_id}
            </span>
            <span class="live-badge"><span class="dot"></span> TRỰC TIẾP</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Đọc ảnh và dựng lớp phủ tương tác
    # Ảnh đọc từ đĩa, đổi sang base64 để nhúng trực tiếp vào HTML.
    img_path = data["image_path"]
    img_b64 = None
    img_w, img_h = 1, 1

    try:
        pil_img = Image.open(img_path)
        img_w, img_h = pil_img.size
        with open(img_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()
    except Exception:
        pass

    # Dựng HTML phủ hộp bbox
    # Tọa độ pixel đổi sang % theo kích thước ảnh để hộp khớp khi ảnh co giãn.
    # Nhãn gian lận gồm Cheat_Paper/cellphone, bài sạch là Answer_paper.
    has_bboxes = any(d.get("face_bbox") for d in detections)

    if img_b64 and has_bboxes:
        bbox_html = ""
        for det in detections:
            bbox = det.get("face_bbox")
            if not bbox or len(bbox) != 4:
                continue

            x1, y1, x2, y2 = bbox
            left_pct = (x1 / img_w) * 100
            top_pct = (y1 / img_h) * 100
            width_pct = ((x2 - x1) / img_w) * 100
            height_pct = ((y2 - y1) / img_h) * 100

            status = det.get("status", "Answer_paper")
            is_sleeping = status in ("Cheat_Paper", "cellphone", "Sleeping")
            cls = "sleeping" if is_sleeping else "normal"
            label_vi = "Gian lận" if is_sleeping else "Bài thi"
            sid = det["student_id"]
            rid = det["result_id"]
            cur_status = "Cheat_Paper" if is_sleeping else "Answer_paper"

            bbox_html += f"""
            <div class="bbox-overlay {cls}"
                 style="left:{left_pct:.2f}%; top:{top_pct:.2f}%;
                        width:{width_pct:.2f}%; height:{height_pct:.2f}%;"
                 data-rid="{rid}" data-status="{cur_status}"
                 onclick="toggleLabel(this)">
                <span class="bbox-tag">{sid} · {label_vi}</span>
            </div>"""

        token = st.session_state.get("access_token_value") or st.session_state.get("token", "")

        # Dùng st.components.v1.html để chạy đầy đủ JS/onclick
        # (st.markdown chặn <script> và onclick vì lý do bảo mật)
        # Nhấn vào bbox sẽ đảo nhãn Cheat_Paper <-> Answer_paper rồi gọi PATCH /ai-result.
        import streamlit.components.v1 as components

        component_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: transparent; }}

            .interactive-frame {{
                position: relative;
                width: 100%;
                border-radius: 14px;
                overflow: hidden;
                background: #0a0a0a;
            }}
            .interactive-frame > img {{
                width: 100%;
                display: block;
            }}

            .bbox-overlay {{
                position: absolute;
                border: 2.5px solid;
                border-radius: 6px;
                cursor: pointer;
                transition: all 0.25s ease;
                z-index: 2;
            }}
            .bbox-overlay.normal {{
                border-color: #22c55e;
                background: rgba(34, 197, 94, 0.10);
            }}
            .bbox-overlay.sleeping {{
                border-color: #ef4444;
                background: rgba(239, 68, 68, 0.12);
            }}
            .bbox-overlay:hover {{
                transform: scale(1.03);
                box-shadow: 0 0 20px rgba(0,0,0,0.4);
                z-index: 3;
            }}
            .bbox-overlay:hover::after {{
                content: "Click để đổi trạng thái";
                position: absolute;
                bottom: -26px;
                left: 50%;
                transform: translateX(-50%);
                font-size: 11px;
                font-weight: 600;
                color: #fff;
                background: rgba(0,0,0,0.75);
                padding: 3px 10px;
                border-radius: 6px;
                white-space: nowrap;
                pointer-events: none;
            }}

            .bbox-tag {{
                position: absolute;
                top: -24px;
                left: -2px;
                padding: 3px 10px;
                border-radius: 6px 6px 0 0;
                font-size: 11px;
                font-weight: 700;
                white-space: nowrap;
                letter-spacing: 0.2px;
                pointer-events: none;
                transition: background 0.3s ease;
            }}
            .bbox-overlay.normal .bbox-tag {{
                background: #22c55e;
                color: #fff;
            }}
            .bbox-overlay.sleeping .bbox-tag {{
                background: #ef4444;
                color: #fff;
            }}

            .bbox-overlay.toggled {{
                animation: toggle-pulse 0.5s ease;
            }}
            @keyframes toggle-pulse {{
                0%   {{ transform: scale(1); }}
                30%  {{ transform: scale(1.08); }}
                60%  {{ transform: scale(0.97); }}
                100% {{ transform: scale(1); }}
            }}

            .frame-hint {{
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 6px;
                margin-top: 10px;
                padding: 8px 16px;
                background: linear-gradient(135deg, #eff6ff, #eef2ff);
                border: 1px solid #c7d2fe;
                border-radius: 10px;
                font-size: 12px;
                font-weight: 600;
                color: #4f46e5;
            }}

            #toast-box {{
                position: fixed;
                bottom: 20px;
                right: 20px;
                z-index: 9999;
                display: flex;
                flex-direction: column;
                gap: 8px;
            }}
            .toast-msg {{
                padding: 10px 18px;
                border-radius: 10px;
                font-size: 13px;
                font-weight: 600;
                color: #fff;
                background: #22c55e;
                box-shadow: 0 4px 16px rgba(0,0,0,0.18);
                animation: toast-in 0.3s ease;
                transition: opacity 0.3s ease, transform 0.3s ease;
            }}
            .toast-msg.err {{ background: #ef4444; }}
            .toast-msg.hide {{ opacity: 0; transform: translateY(10px); }}
            @keyframes toast-in {{
                from {{ opacity: 0; transform: translateY(20px); }}
                to   {{ opacity: 1; transform: translateY(0); }}
            }}
        </style>
        </head>
        <body>
            <div class="interactive-frame">
                <img src="data:image/jpeg;base64,{img_b64}" alt="Frame">
                {bbox_html}
            </div>
            <div class="frame-hint">
                <span>👆</span> Nhấn vào nhãn trên ảnh để thay đổi trạng thái
            </div>
            <div id="toast-box"></div>

            <script>
            const API = '{API_BASE_URL}';
            const TK = '{token}';

            function toggleLabel(el) {{
                const rid = el.dataset.rid;
                const cur = el.dataset.status;
                const nxt = cur === 'Cheat_Paper' ? 'Answer_paper' : 'Cheat_Paper';
                const viTxt = nxt === 'Cheat_Paper' ? 'Gian lận' : 'Bài thi';
                const tag = el.querySelector('.bbox-tag');
                const sid = tag.textContent.split(' · ')[0];

                el.classList.remove('sleeping','normal');
                el.classList.add(nxt === 'Cheat_Paper' ? 'sleeping' : 'normal');
                el.dataset.status = nxt;
                tag.textContent = sid + ' · ' + viTxt;
                el.classList.add('toggled');
                setTimeout(function() {{ el.classList.remove('toggled'); }}, 600);

                fetch(API + '/ai-result/' + rid, {{
                    method: 'PATCH',
                    headers: {{
                        'Content-Type': 'application/json',
                        'Authorization': 'Bearer ' + TK
                    }},
                    body: JSON.stringify({{status: nxt}})
                }}).then(function(r) {{
                    if (r.ok) {{
                        showToast('✅ ' + sid + ' → ' + viTxt);
                    }} else {{
                        showToast('❌ Lỗi cập nhật', 'err');
                        el.classList.remove('sleeping','normal');
                        el.classList.add(cur === 'Cheat_Paper' ? 'sleeping' : 'normal');
                        el.dataset.status = cur;
                        tag.textContent = sid + ' · ' + (cur === 'Cheat_Paper' ? 'Gian lận' : 'Bài thi');
                    }}
                }}).catch(function() {{
                    showToast('❌ Lỗi kết nối', 'err');
                }});
            }}

            function showToast(msg, type) {{
                var box = document.getElementById('toast-box');
                var t = document.createElement('div');
                t.className = 'toast-msg ' + (type || '');
                t.textContent = msg;
                box.appendChild(t);
                setTimeout(function() {{
                    t.classList.add('hide');
                    setTimeout(function() {{ t.remove(); }}, 300);
                }}, 2500);
            }}
            </script>
        </body>
        </html>
        """

        # Tính chiều cao khối nhúng theo tỉ lệ ảnh + thanh gợi ý
        aspect = img_h / img_w if img_w > 0 else 0.75
        estimated_height = int(700 * aspect) + 60  # 700px xấp xỉ rộng khối chứa + thanh gợi ý
        components.html(component_html, height=estimated_height, scrolling=False)
    else:
        # Dự phòng: hiện ảnh thường khi không có bbox
        st.image(img_path, use_container_width=True)

# ── PHẢI: số liệu và phân bổ ─────────────────────────────
with right_col:
    # Tiêu đề khối bên phải
    st.markdown('<div class="right-section-title">Thống số khung hình</div>', unsafe_allow_html=True)

    # KPI: tổng số học sinh
    st.markdown(f"""
    <div class="kpi-mini">
        <div class="kpi-left">
            <div class="kpi-label">TỔNG HỌC SINH</div>
            <div class="kpi-val">{total}</div>
        </div>
        <span class="kpi-change up">↗ 01%</span>
    </div>
    """, unsafe_allow_html=True)

    # KPI: học sinh buồn ngủ/gian lận
    sleep_change_cls = "down" if sleeping > 0 else "up"
    st.markdown(f"""
    <div class="kpi-mini alert">
        <div class="kpi-left">
            <div class="kpi-label">HỌC SINH BUỒN NGỦ</div>
            <div class="kpi-val red">{sleeping:02d}</div>
        </div>
        <span class="kpi-change {sleep_change_cls}">↑ +{sleeping_pct}%</span>
    </div>
    """, unsafe_allow_html=True)

    # KPI: độ tin cậy của AI
    st.markdown(f"""
    <div class="kpi-mini">
        <div class="kpi-left">
            <div class="kpi-label">ĐỘ TIN CẬY AI</div>
            <div class="kpi-val blue">{conf}%</div>
        </div>
        <span class="kpi-change neutral">~ 0.0%</span>
    </div>
    """, unsafe_allow_html=True)

    # Khối phân bổ trạng thái
    st.markdown('<div class="dist-section">', unsafe_allow_html=True)
    st.markdown('<div class="dist-title">Phân bổ trạng thái</div>', unsafe_allow_html=True)

    # Nhóm tập trung
    st.markdown(f"""
    <div class="dist-row">
        <span class="dist-label">Tập trung</span>
        <span class="dist-pct">{focus_pct}%</span>
    </div>
    """, unsafe_allow_html=True)
    st.progress(focus_pct / 100 if focus_pct > 0 else 0)

    # Nhóm buồn ngủ/gian lận
    st.markdown(f"""
    <div class="dist-row">
        <span class="dist-label">Buồn ngủ</span>
        <span class="dist-pct">{sleeping_pct}%</span>
    </div>
    """, unsafe_allow_html=True)
    st.progress(sleeping_pct / 100 if sleeping_pct > 0 else 0)

    st.markdown('</div>', unsafe_allow_html=True)

# ── Bảng danh sách phát hiện ──────────────────────────────
st.markdown("""
<div class="table-card">
    <div class="table-card-title">Danh sách phát hiện</div>
</div>
""", unsafe_allow_html=True)

if not detections:
    st.info("Không có kết quả phát hiện.")
else:
    # Tiêu đề bảng
    h1, h2, h3, h4 = st.columns([1.2, 1.5, 1.5, 1.2])
    h1.markdown("<div class='tbl-head'>ID HỌC SINH</div>", unsafe_allow_html=True)
    h2.markdown("<div class='tbl-head'>HỌ VÀ TÊN</div>", unsafe_allow_html=True)
    h3.markdown("<div class='tbl-head'>TRẠNG THÁI</div>", unsafe_allow_html=True)
    h4.markdown("<div class='tbl-head'>ĐỘ TIN CẬY</div>", unsafe_allow_html=True)

    # Các hàng chỉ đọc — sửa nhãn thực hiện trên ảnh phía trên
    for row in detections:
        result_id = row.get("result_id")
        if not result_id:
            continue

        status = row.get("status", "Unknown")
        confidence = row.get("confidence", 0) * 100

        c1, c2, c3, c4 = st.columns([1.2, 1.5, 1.5, 1.2])

        c1.markdown(
            f"<div class='tbl-cell'>{row.get('student_id', '-')}</div>",
            unsafe_allow_html=True,
        )

        idx = row.get("student_id", "HS0").replace("HS", "")
        c2.markdown(
            f"<div class='tbl-cell'>Học sinh {idx}</div>",
            unsafe_allow_html=True,
        )

        if status in ("Cheat_Paper", "cellphone", "Sleeping"):
            tag_cls = "sleeping"
            tag_text = "Gian lận"
        else:
            tag_cls = "normal"
            tag_text = "Bài thi"

        c3.markdown(
            f"<div class='tbl-cell'><span class='status-tag {tag_cls}'>{tag_text}</span></div>",
            unsafe_allow_html=True,
        )

        c4.markdown(
            f"<div class='tbl-cell'>{confidence:.1f}%</div>",
            unsafe_allow_html=True,
        )