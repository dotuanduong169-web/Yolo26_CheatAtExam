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
    cls_online = "active" if active_key in ("online_exam", "thionline") else ""

    from utils.http import auth_query_params
    aqs = auth_query_params()

    # ── Trigger điều hướng native (ẩn): visual giữ nguyên HTML,
    # click trên thanh nav sẽ bấm nút ẩn này → st.switch_page (rerun nhẹ,
    # không reload toàn trình duyệt nên không chớp màn hình) ──
    _NAV_TARGETS = (
        ("home", "pages/home.py"),
        ("history", "pages/history.py"),
        ("devices", "pages/devices.py"),
        ("statistics", "pages/statistics.py"),
        ("users", "pages/users.py"),
        ("online_exam", "pages/online_exam.py"),
    )
    st.markdown(
        "<style>div[class*='st-key-hidden_nav_'],div[data-testid^='st-key-hidden_nav_']"
        "{display:none!important;height:0!important;min-height:0!important;margin:0!important;"
        "padding:0!important;visibility:hidden!important;overflow:hidden!important}</style>",
        unsafe_allow_html=True,
    )
    for _nav_key, _nav_target in _NAV_TARGETS:
        if st.button("", key=f"hidden_nav_{_nav_key}"):
            st.switch_page(_nav_target)

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
        '<div class="global-nav-bar">'
        '  <div class="nav-container">'
        f'    <a href="/home?{aqs}" target="_self" data-page="home" class="nav-tab-btn {cls_home}">Giám sát</a>'
        f'    <a href="/history?{aqs}" target="_self" data-page="history" class="nav-tab-btn {cls_hist}">Lịch sử</a>'
        f'    <a href="/devices?{aqs}" target="_self" data-page="devices" class="nav-tab-btn {cls_dev}">Thiết bị</a>'
        f'    <a href="/statistics?{aqs}" target="_self" data-page="statistics" class="nav-tab-btn {cls_stats}">Thống kê</a>'
        f'    <a href="/users?{aqs}" target="_self" data-page="users" class="nav-tab-btn {cls_set}">Cài đặt</a>'
        f'    <a href="/online_exam?{aqs}" target="_self" data-page="online_exam" class="nav-tab-btn {cls_online}">Thi online</a>'
        '  </div>'
        '</div>'
        '<script>'
        '(function() {'
        '  window.addEventListener("error", function(e) {'
        '    if (e && e.message && typeof e.message === "string" && e.message.indexOf("toLowerCase") >= 0) {'
        '      e.preventDefault();'
        '      e.stopPropagation();'
        '      return true;'
        '    }'
        '  }, true);'
        ''
        '  function setupNavTabs() {'
        '    var navLinks = document.querySelectorAll(".global-nav-bar .nav-tab-btn");'
        '    if (!navLinks || !navLinks.length) return;'
        '    navLinks.forEach(function(btn) {'
        '      if (btn.dataset.bound) return;'
        '      btn.dataset.bound = "1";'
        '      btn.onclick = function(e) {'
        '        e.preventDefault();'
        '        if (this.classList.contains("active")) {'
        '          return false;'
        '        }'
        '        var pageKey = this.getAttribute("data-page") || "";'
        '        navLinks.forEach(function(b) { b.classList.remove("active"); });'
        '        this.classList.add("active");'
        '        try {'
        '          var frame = window.parent.document;'
        '          var hid = frame.querySelector("[data-testid=\'st-key-hidden_nav_" + pageKey + "\'] button");'
        '          if (hid) { hid.click(); return false; }'
        '        } catch(err) {}'
        '        return false;'
        '      };'
        '    });'
        '  }'
        '  setupNavTabs();'
        '  setTimeout(setupNavTabs, 200);'
        '})();'
        '</script>'
    )
    st.markdown(header_html, unsafe_allow_html=True)

    # Flush toast xếp hàng tại top-level để luôn neo ngoài, đúng góc hệ thống
    from utils.notify import flush as _flush_toasts

    _flush_toasts()
