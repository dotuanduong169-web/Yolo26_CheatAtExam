# -*- coding: utf-8 -*-
"""Trang lịch sử phiên: tìm kiếm, phân trang và xóa phiên.
Luồng chính: tải danh sách và tổng hợp -> vẽ thẻ tóm tắt -> vẽ bảng -> xử lý phân trang."""

import streamlit as st

from components.app_sidebar import render_sidebar
from services.history_api import (
    delete_session,
    get_history,
    get_history_summary,
)
from utils.auth_guard import require_auth
from utils.hide_streamlit_sidebar import hide_sidebar
from utils.http import init_session_state
from utils.load_css import load_css
from utils.render_header import render_page_header

# ── Cấu hình trang ────────────────────────────────────────
st.set_page_config(layout="wide", page_title="Lịch sử")

st.markdown(load_css("styles/sidebar.css"), unsafe_allow_html=True)
st.markdown(load_css("styles/history.css"), unsafe_allow_html=True)

init_session_state()
require_auth()

PAGE_SIZE = 5


def _fetch_history(session, search: str = "", page: int = 1) -> dict | None:
    """Tải danh sách phiên và số liệu tổng hợp qua tầng service."""
    skip = (page - 1) * PAGE_SIZE
    sessions = get_history(session, search=search, skip=skip, limit=PAGE_SIZE)
    summary = get_history_summary(session)

    if sessions is None or summary is None:
        return None

    return {
        "sessions": sessions,
        "total_sessions": summary.get("total_sessions", 0),
        "month_sessions": summary.get("month_sessions", 0),
    }


def handle_delete(session_id: int) -> None:
    """Chạy xóa phiên và hiện kết quả cho người dùng."""
    res = delete_session(st.session_state.client, session_id)
    if not res:
        st.error("[ERROR] Không kết nối được server")
        return
    if res.status_code == 200:
        st.success("[OK] Xóa phiên thành công")
        st.rerun()
    elif res.status_code == 400:
        st.error("[ERROR] Không thể xóa phiên đang chạy")
    elif res.status_code == 404:
        st.error("[ERROR] Không tìm thấy session")
    else:
        st.error(f"[ERROR] Lỗi server: {res.text}")


@st.dialog("Xac nhan xoa session")
def confirm_delete(session_id: int):
    """Hiện hộp thoại xác nhận trước khi xóa phiên."""
    st.warning("Bạn có chắc muốn xóa session này không?")
    st.caption("Hành động này sẽ xóa toàn bộ frames và dữ liệu liên quan.")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Huy", use_container_width=True):
            st.rerun()
    with c2:
        if st.button("Xoa", type="primary", use_container_width=True):
            handle_delete(session_id)


# ── Thanh bên ─────────────────────────────────────────────
hide_sidebar()
render_sidebar(active="history")

# ── Trạng thái session cho phân trang ─────────────────────
if "hist_page" not in st.session_state:
    st.session_state.hist_page = 1
if "hist_search" not in st.session_state:
    st.session_state.hist_search = ""

# ── Nút ẩn để chuyển trang lịch sử ────────────────────────
# JS sẽ bấm các nút này khi người dùng nhấn số trang
col_hidden1, col_hidden2, col_hidden3, col_hidden4, col_hidden5 = st.columns(5)
with col_hidden1:
    st.markdown('<div id="hide-nav-row"></div>', unsafe_allow_html=True)
    if st.button("Go to 1", key="hist_go_1", disabled=True):
        st.session_state.hist_page = 1
with col_hidden2:
    if st.button("Go to 2", key="hist_go_2", disabled=True):
        st.session_state.hist_page = 2
with col_hidden3:
    if st.button("Go to 3", key="hist_go_3", disabled=True):
        st.session_state.hist_page = 3
with col_hidden4:
    if st.button("Go to 4", key="hist_go_4", disabled=True):
        st.session_state.hist_page = 4
with col_hidden5:
    if st.button("Go to 5", key="hist_go_5", disabled=True):
        st.session_state.hist_page = 5

# Ẩn hàng nút này
st.markdown("""
<style>
    /* Dự phòng ẩn hàng nút khi có thể */
    [data-testid="stHorizontalBlock"]:has(#hide-nav-row) {
        display: none !important;
    }
    
    /* Nút popover ở cột thao tác: bỏ viền cho gọn */
    div[data-testid="column"]:last-child div[data-testid="stPopover"] button {
        border: none !important;
        background: transparent !important;
        box-shadow: none !important;
        padding: 4px 8px !important;
        min-height: unset !important;
        font-size: 20px !important;
        color: #64748b !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }
    div[data-testid="column"]:last-child div[data-testid="stPopover"] button:hover {
        background-color: #f1f5f9 !important;
        color: #0f172a !important;
        border-radius: 4px !important;
    }
    /* Ẩn biểu tượng mũi tên của nút popover */
    div[data-testid="column"]:last-child div[data-testid="stPopover"] button svg {
        display: none !important;
    }
</style>
<script>
    (function() {
        const marker = document.getElementById('hide-nav-row');
        if (marker) {
            const row = marker.closest('[data-testid="stHorizontalBlock"]');
            if (row) {
                row.style.display = 'none';
                row.style.height = '0';
                row.style.margin = '0';
                row.style.padding = '0';
            }
        }
    })();
</script>
""", unsafe_allow_html=True)


# ── Tiêu đề trang ─────────────────────────────────────────
render_page_header("Lịch sử phân tích")

# ── Tải dữ liệu ───────────────────────────────────────────
data = _fetch_history(
    st.session_state.client,
    search=st.session_state.hist_search,
    page=st.session_state.hist_page,
)
if not data:
    st.stop()

# ── Thẻ tóm tắt ───────────────────────────────────────────
col_s1, col_s2, col_s3 = st.columns([1, 1, 2])

with col_s1:
    st.markdown(f"""
    <div class="summary-card">
        <div class="label">TỔNG PHIÊN PHÂN TÍCH</div>
        <div class="value">{data['total_sessions']:,}</div>
        <div class="trend up">&uarr; +12%</div>
    </div>
    """, unsafe_allow_html=True)

with col_s2:
    st.markdown(f"""
    <div class="summary-card">
        <div class="label">PHIÊN TRONG THÁNG</div>
        <div class="value">{data['month_sessions']:,}</div>
        <div class="trend neutral">Tháng hiện tại</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("")  # spacer

# ── Ô tìm kiếm ────────────────────────────────────────────
search_val = st.text_input(
    "Tìm kiếm",
    value=st.session_state.hist_search,
    placeholder="Tim kiem theo ma phien hoac ten lop hoc...",
    label_visibility="collapsed",
)

# Đổi từ khóa tìm kiếm thì quay về trang 1
if search_val != st.session_state.hist_search:
    st.session_state.hist_search = search_val
    st.session_state.hist_page = 1
    st.rerun()

# ── Dữ liệu trang hiện tại ─────────────────────────────────
sessions = data["sessions"]
total_sessions_count = data["total_sessions"]
total_pages = max((total_sessions_count - 1) // PAGE_SIZE + 1, 1)
current_page = st.session_state.hist_page

# ── Bảng phiên ────────────────────────────────────────────
st.markdown('<div class="table-card">', unsafe_allow_html=True)

# Tiêu đề bảng
st.markdown("""
<div class="table-header-row">
    <span>MÃ PHIÊN</span>
    <span>LỚP HỌC</span>
    <span>NGÀY THỰC HIỆN</span>
    <span>SỐ LẦN PHÂN TÍCH</span>
    <span style="text-align:right">THAO TÁC</span>
</div>
""", unsafe_allow_html=True)

# Các hàng của bảng
if not sessions:
    st.markdown("""
    <div style="padding:40px 24px; text-align:center; color:#9ca3af;">
        <div style="font-size:14px; font-weight:500;">Khong tim thay phien nao</div>
    </div>
    """, unsafe_allow_html=True)
else:
    for sess in sessions:
        sid = sess["session_id"]
        class_id = sess["class_id"]
        date_str = sess["date"]
        frame_count = sess["frame_count"]

        # Hàng trong bảng kèm menu thao tác popover
        row_cols = st.columns([1.2, 2, 1.5, 1.2, 0.5])
        with row_cols[0]:
            st.markdown(f'<span class="cell-session-id">#SESS-{sid}</span>', unsafe_allow_html=True)
        with row_cols[1]:
            st.markdown(f'<span class="cell-class">{class_id}</span>', unsafe_allow_html=True)
        with row_cols[2]:
            st.markdown(f'<span class="cell-date">{date_str}</span>', unsafe_allow_html=True)
        with row_cols[3]:
            st.markdown(f'<span class="cell-count">{frame_count}</span>', unsafe_allow_html=True)
        with row_cols[4]:
            with st.popover("⋮", use_container_width=False):
                if st.button("Xem chi tiet", key=f"view_{sid}", use_container_width=True):
                    st.session_state.selected_session = sid
                    st.switch_page("pages/session_detail.py")
                if st.button("Xoa phien", key=f"del_{sid}", use_container_width=True):
                    confirm_delete(sid)

# ── Tính khoảng hiển thị ──────────────────────────────────
start_idx = (current_page - 1) * PAGE_SIZE + 1
end_idx = min(current_page * PAGE_SIZE, total_sessions_count)

# ── Hàng phân trang ─────────────────────────────────────────
# Một hàng Streamlit duy nhất — tạo kiểu bằng CSS cho khớp chân bảng.
st.markdown('<div id="hist-pagination-row">', unsafe_allow_html=True)
info_col, prev_col, nums_col, next_col = st.columns([4, 1, 4, 1], gap="small")

with info_col:
    st.markdown(
        f"<div class='pagination-info'>Hiển thị {start_idx} – {end_idx} của {total_sessions_count} kết quả</div>",
        unsafe_allow_html=True,
    )

# Dựng HTML số trang
page_buttons_html = []
if total_pages <= 7:
    page_range = range(1, total_pages + 1)
else:
    if current_page <= 3:
        page_range = list(range(1, 5)) + [-1, total_pages]
    elif current_page >= total_pages - 2:
        page_range = [1, -1] + list(range(total_pages - 3, total_pages + 1))
    else:
        page_range = [1, -1, current_page - 1, current_page, current_page + 1, -1, total_pages]

for p in page_range:
    if p == -1:
        page_buttons_html.append('<span class="page-ellipsis">…</span>')
    else:
        active = "active" if p == current_page else ""
        page_buttons_html.append(f'<span class="page-btn {active}" data-page="{p}">{p}</span>')

with nums_col:
    st.markdown(
        f"<div class='pagination-controls'>{''.join(page_buttons_html)}</div>",
        unsafe_allow_html=True,
    )

with prev_col:
    if st.button("‹", key="pg_prev_btn", disabled=(current_page <= 1)):
        st.session_state.hist_page -= 1
        st.rerun()

with next_col:
    if st.button("›", key="pg_next_btn", disabled=(current_page >= total_pages)):
        st.session_state.hist_page += 1
        st.rerun()

st.markdown('</div>', unsafe_allow_html=True)

# ── JS bắt click vào số trang ─────────────────────────────
st.markdown(f"""
<script>
    document.querySelectorAll('#hist-pagination-row .page-btn[data-page]').forEach(btn => {{
        btn.style.cursor = 'pointer';
        btn.addEventListener('click', function() {{
            const page = parseInt(this.dataset.page);
            // Giả lập bấm nút ẩn tương ứng
            const hiddenBtn = document.querySelector('button[data-testid*="hist_go_' + page + '"]');
            if (hiddenBtn) hiddenBtn.click();
        }});
    }});
</script>
""", unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)

