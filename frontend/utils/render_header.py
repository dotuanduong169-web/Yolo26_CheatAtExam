import streamlit as st
from utils.load_css import load_css
from utils.logo import logo_img


def render_page_header(title: str, active: str | None = None):
    """Vẽ thanh header chung: logo ExamCheat AI + tiêu đề trang + thanh tab điều hướng cố định.
    active: key trang hiện tại (home/events/statistics/history/devices/setting).
    """
    st.markdown(load_css("styles/header.css"), unsafe_allow_html=True)
    st.markdown(load_css("styles/app_theme.css"), unsafe_allow_html=True)

    from datetime import datetime
    today_str = datetime.now().strftime("%d/%m/%Y")

    user_name = st.session_state.get("user_fullname") or st.session_state.get("username") or "Cán bộ coi thi"
    role_raw = str(st.session_state.get("user_role", "teacher")).lower()
    role_label = "Quản trị viên" if role_raw == "admin" else "Cán bộ coi thi"
    avatar_letter = user_name.strip()[:1].upper() if user_name.strip() else "U"

    # Xác định class active cho đúng 5 tab điều hướng chính
    active_key = (active or "").lower()
    cls_home = "active" if active_key in ("home", "giamsat") else ""
    cls_hist = "active" if active_key in ("history", "lichsu", "events", "sukien") else ""
    cls_dev = "active" if active_key in ("devices", "thietbi") else ""
    cls_stats = "active" if active_key in ("statistics", "thongke") else ""
    cls_set = "active" if active_key in ("setting", "users", "caidat") else ""

    header_html = (
        '<div class="global-top-bar">'
        '  <div class="top-logo-section">'
        f'    <div class="top-logo-box">{logo_img(36, 8)}</div>'
        '    <div class="top-logo-text">'
        '      <div class="top-logo-main">ExamCheat AI</div>'
        '      <div class="top-logo-sub">Giám sát thi thông minh</div>'
        '    </div>'
        '  </div>'
        f'  <div class="top-page-title">{title}</div>'
        '  <div class="top-meta-right">'
        '    <div class="header-user-badge">'
        f'      <div class="header-avatar">{avatar_letter}</div>'
        '      <div class="header-user-info">'
        f'        <span class="header-user-name">{user_name}</span>'
        f'        <span class="header-role-chip {role_raw}">{role_label}</span>'
        '      </div>'
        '    </div>'
        '    <div class="header-date-chip" title="Ngày làm việc">'
        '      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '        <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>'
        '        <line x1="16" y1="2" x2="16" y2="6"/>'
        '        <line x1="8" y1="2" x2="8" y2="6"/>'
        '        <line x1="3" y1="10" x2="21" y2="10"/>'
        '      </svg>'
        f'      <span>{today_str}</span>'
        '    </div>'
        '    <a href="/login?logout=1" target="_self" class="header-logout-btn" onclick="try{localStorage.removeItem(\'examcheat_auth\');}catch(e){};try{window.localStorage.removeItem(\'examcheat_auth\');}catch(e){};try{window.parent.localStorage.removeItem(\'examcheat_auth\');}catch(e){};try{window.top.localStorage.removeItem(\'examcheat_auth\');}catch(e){};window.top.location.href=\'/login?logout=1\';return false;" title="Đăng xuất khỏi hệ thống">'
        '      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '        <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>'
        '        <polyline points="16 17 21 12 16 7"/>'
        '        <line x1="21" y1="12" x2="9" y2="12"/>'
        '      </svg>'
        '      <span>Đăng xuất</span>'
        '    </a>'
        '  </div>'
        '</div>'
    )
    st.markdown(header_html, unsafe_allow_html=True)

    # ── THANH ĐIỀU HƯỚNG 5 TRANG NATIVE STREAMLIT SPA (KHÔNG RELOAD, KHÔNG CHỚP TRẮNG) ──
    nav_c1, nav_c2, nav_c3, nav_c4, nav_c5 = st.columns(5, gap="small")
    with nav_c1:
        st.page_link("pages/home.py", label="Giám sát", use_container_width=True)
    with nav_c2:
        st.page_link("pages/history.py", label="Lịch sử", use_container_width=True)
    with nav_c3:
        st.page_link("pages/devices.py", label="Thiết bị", use_container_width=True)
    with nav_c4:
        st.page_link("pages/statistics.py", label="Thống kê", use_container_width=True)
    with nav_c5:
        st.page_link("pages/users.py", label="Cài đặt", use_container_width=True)

    # Đảm bảo tab tương ứng luôn active kể cả khi ở các trang con (session_detail, event_detail)
    active_idx_map = {
        "home": 1, "giamsat": 1,
        "history": 2, "lichsu": 2, "events": 2, "sukien": 2,
        "devices": 3, "thietbi": 3,
        "statistics": 4, "thongke": 4,
        "setting": 5, "users": 5, "caidat": 5,
    }
    cur_idx = active_idx_map.get(active_key, 1)
    active_css = f"""
    <style>
    div[data-testid="stHorizontalBlock"]:has(div[data-testid="stPageLink-NavLink"]) div[data-testid="column"]:nth-child({cur_idx}) div[data-testid="stPageLink-NavLink"] a {{
        background-color: #eff6ff !important;
        border-color: #bfdbfe !important;
        color: #2563eb !important;
        font-weight: 600 !important;
        box-shadow: 0 1px 3px rgba(37, 99, 235, 0.12) !important;
    }}
    div[data-testid="stHorizontalBlock"]:has(div[data-testid="stPageLink-NavLink"]) div[data-testid="column"]:nth-child({cur_idx}) div[data-testid="stPageLink-NavLink"] a * {{
        color: #2563eb !important;
        font-weight: 600 !important;
    }}
    </style>
    """
    st.markdown(active_css, unsafe_allow_html=True)



    # Flush toast xếp hàng tại top-level để luôn neo ngoài, đúng góc hệ thống
    from utils.notify import flush as _flush_toasts

    _flush_toasts()
