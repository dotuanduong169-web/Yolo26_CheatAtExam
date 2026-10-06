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

    from utils.http import auth_query_params
    aqs = auth_query_params()

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
        '        if (this.classList.contains("active")) {'
        '          e.preventDefault();'
        '          return false;'
        '        }'
        '        var pageKey = this.getAttribute("data-page") || "";'
        '        var hiddenLink = document.querySelector("#spa-nav-hidden a[href*=\'" + pageKey + "\']");'
        '        if (hiddenLink) {'
        '          e.preventDefault();'
        '          e.stopPropagation();'
        '          navLinks.forEach(function(b) { b.classList.remove("active"); });'
        '          this.classList.add("active");'
        '          try { hiddenLink.click(); return false; } catch(err) {}'
        '        }'
        '        var dest = this.getAttribute("href") || ("/" + pageKey);'
        '        window.top.location.href = dest;'
        '        return false;'
        '      };'
        '    });'
        '    var otherLinks = document.querySelectorAll(".action-svg-btn, .history-pagination a");'
        '    otherLinks.forEach(function(el) {'
        '      el.setAttribute("target", "_self");'
        '      el.removeAttribute("rel");'
        '    });'
        '  }'
        '  setupNavTabs();'
        '  setTimeout(setupNavTabs, 50);'
        '  setTimeout(setupNavTabs, 150);'
        '  setTimeout(setupNavTabs, 500);'
        '})();'
        '</script>'
    )
    st.markdown(header_html, unsafe_allow_html=True)

    # ── HIDDEN STREAMLIT SPA ROUTING: Cho phép click tab chuyển trang nội bộ qua WebSocket ──
    st.markdown(
        '<div id="spa-nav-hidden" style="display:none!important; visibility:hidden; position:absolute; width:0; height:0; overflow:hidden; pointer-events:none;">',
        unsafe_allow_html=True,
    )
    st.page_link("pages/home.py", label="home")
    st.page_link("pages/history.py", label="history")
    st.page_link("pages/devices.py", label="devices")
    st.page_link("pages/statistics.py", label="statistics")
    st.page_link("pages/users.py", label="users")
    st.markdown('</div>', unsafe_allow_html=True)

    # Flush toast xếp hàng tại top-level để luôn neo ngoài, đúng góc hệ thống
    from utils.notify import flush as _flush_toasts

    _flush_toasts()
