import streamlit as st
from utils.load_css import load_css


def render_page_header(title: str, active: str | None = None):
    """Vẽ thanh header chung: logo ExamCheat AI + tiêu đề trang + thanh tab điều hướng cố định.
    active: key trang hiện tại (home/events/statistics/history/devices/setting).
    """
    st.markdown(load_css("styles/header.css"), unsafe_allow_html=True)
    st.markdown(load_css("styles/app_theme.css"), unsafe_allow_html=True)

    session_id = st.session_state.get("session_id")
    is_running = st.session_state.get("running", False)
    user_name = st.session_state.get("user_fullname") or st.session_state.get("username") or "Cán bộ coi thi"
    role_raw = st.session_state.get("user_role", "teacher")
    role_label = "Quản trị viên" if role_raw == "admin" else "Cán bộ coi thi"

    if is_running and session_id:
        session_text = f"Phòng #{session_id}"
        session_badge_cls = "online"
        session_badge_text = "Đang giám sát"
    else:
        session_text = "Chưa mở ca thi"
        session_badge_cls = ""
        session_badge_text = "Hệ thống sẵn sàng"

    # Xác định class active cho từng tab điều hướng
    active_key = (active or "").lower()
    cls_home = "active" if active_key in ("home", "giamsat") else ""
    cls_events = "active" if active_key in ("events", "sukien") else ""
    cls_stats = "active" if active_key in ("statistics", "thongke") else ""
    cls_hist = "active" if active_key in ("history", "lichsu") else ""
    cls_dev = "active" if active_key in ("devices", "thietbi") else ""
    cls_set = "active" if active_key in ("setting", "users", "caidat") else ""

    header_html = (
        '<div class="global-top-bar">'
        '  <div class="top-logo-section">'
        '    <div class="top-logo-box">'
        '      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">'
        '        <path d="M3 3v18h18" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
        '        <path d="M7 14l4-4 4 4 6-6" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
        '        <path d="M21 8v-4h-4" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
        '      </svg>'
        '    </div>'
        '    <div class="top-logo-text">'
        '      <div class="top-logo-main">ExamCheat AI</div>'
        '      <div class="top-logo-sub">Giám sát thi thông minh</div>'
        '    </div>'
        '  </div>'
        f'  <div class="top-page-title">{title}</div>'
        '  <div class="top-meta-right">'
        f'    <div>Ca thi: <strong>{session_text}</strong></div>'
        f'    <div>{role_label}: <strong>{user_name}</strong></div>'
        f'    <div>Trạng thái: <span class="badge {session_badge_cls}">{session_badge_text}</span></div>'
        '    <a href="/login?logout=1" class="header-logout-btn" onclick="try{localStorage.removeItem(\'examcheat_auth\');}catch(e){};try{window.localStorage.removeItem(\'examcheat_auth\');}catch(e){};try{window.parent.localStorage.removeItem(\'examcheat_auth\');}catch(e){};try{window.top.localStorage.removeItem(\'examcheat_auth\');}catch(e){};window.top.location.href=\'/login?logout=1\';return false;" title="Đăng xuất khỏi hệ thống">'
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
        f'    <a href="/home" target="_self" data-page="home" class="nav-tab-btn {cls_home}">Giám sát</a>'
        f'    <a href="/events" target="_self" data-page="events" class="nav-tab-btn {cls_events}">Sự kiện</a>'
        f'    <a href="/statistics" target="_self" data-page="statistics" class="nav-tab-btn {cls_stats}">Thống kê</a>'
        f'    <a href="/history" target="_self" data-page="history" class="nav-tab-btn {cls_hist}">Lịch sử</a>'
        f'    <a href="/devices" target="_self" data-page="devices" class="nav-tab-btn {cls_dev}">Thiết bị</a>'
        f'    <a href="/users" target="_self" data-page="users" class="nav-tab-btn {cls_set}">Cài đặt</a>'
        '  </div>'
        '</div>'
        '<script>'
        '(function() {'
        '  function findStreamlitNavLink(pageKey) {'
        '    var selectors = ['
        '      "a[data-testid=\'stSidebarNavLink\']",'
        '      "section[data-testid=\'stSidebar\'] a",'
        '      "[data-testid=\'stSidebarNav\'] a",'
        '      "ul[data-testid=\'stSidebarNavItems\'] a",'
        '      "div[data-testid=\'stPageLink-NavLink\'] a"'
        '    ];'
        '    var allLinks = document.querySelectorAll(selectors.join(", "));'
        '    for (var i = 0; i < allLinks.length; i++) {'
        '      var a = allLinks[i];'
        '      var h = (a.getAttribute("href") || "").toLowerCase().trim();'
        '      if (h.endsWith("/" + pageKey) || h.endsWith(pageKey) || h === pageKey || h.indexOf("/" + pageKey) >= 0) {'
        '        return a;'
        '      }'
        '    }'
        '    return null;'
        '  }'
        ''
        '  function setupNavTabs() {'
        '    var navLinks = document.querySelectorAll(".global-nav-bar .nav-tab-btn");'
        '    navLinks.forEach(function(btn) {'
        '      btn.onclick = function(e) {'
        '        e.preventDefault();'
        '        e.stopPropagation();'
        '        if (this.classList.contains("active")) { return false; }'
        '        var pageKey = this.getAttribute("data-page") || "";'
        '        var dest = this.getAttribute("href") || ("/" + pageKey);'
        '        navLinks.forEach(function(b) { b.classList.remove("active"); });'
        '        this.classList.add("active");'
        '        var stLink = findStreamlitNavLink(pageKey);'
        '        if (stLink) {'
        '          try { stLink.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true, view: window })); } catch(err) {}'
        '          stLink.click();'
        '          return false;'
        '        }'
        '        try {'
        '          var raw = window.localStorage.getItem("examcheat_auth");'
        '          if (raw) {'
        '            var d = JSON.parse(raw);'
        '            if (d && d.token) {'
        '              var sep = dest.indexOf("?") >= 0 ? "&" : "?";'
        '              dest = dest + sep + "auth=" + encodeURIComponent(d.token) +'
        '                     "&role=" + encodeURIComponent(d.role || "") +'
        '                     "&u=" + encodeURIComponent(d.username || "");'
        '            }'
        '          }'
        '        } catch(ex) {}'
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
        '  setTimeout(setupNavTabs, 60);'
        '  setTimeout(setupNavTabs, 200);'
        '  setTimeout(setupNavTabs, 600);'
        '})();'
        '</script>'
    )
    st.markdown(header_html, unsafe_allow_html=True)
