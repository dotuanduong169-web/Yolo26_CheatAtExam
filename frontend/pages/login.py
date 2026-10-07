"""Trang đăng nhập."""

import streamlit as st
from utils.notify import flush as flush_toasts
from utils.notify import notify

from services.auth_api import login
from utils.http import init_session_state
from utils.load_css import load_css

# ── Config ──────────────────────────────────────────────────
st.set_page_config(layout="centered", initial_sidebar_state="collapsed", page_title="Đăng nhập")

init_session_state()

# ── Xử lý khi người dùng yêu cầu Đăng xuất ────────────────────
is_logout_requested = st.query_params.get("logout") == "1"
if is_logout_requested:
    # Xóa sạch phiên và các query parameters
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    for qk in list(st.query_params.keys()):
        del st.query_params[qk]
    init_session_state()
    st.components.v1.html(
        """
        <script>
        (function() {
            try { localStorage.removeItem("examcheat_auth"); } catch(e) {}
            try { window.localStorage.removeItem("examcheat_auth"); } catch(e) {}
            try { window.parent.localStorage.removeItem("examcheat_auth"); } catch(e) {}
            try { window.top.localStorage.removeItem("examcheat_auth"); } catch(e) {}
            if (window.top.location.search.includes("logout")) {
                window.top.history.replaceState({}, document.title, "/login");
            }
        })();
        </script>
        """,
        height=0,
        width=0,
    )
elif not st.session_state.get("access_token_value") and not st.query_params.get("auth"):
    # Chỉ tự động khôi phục phiên nếu KHÔNG phải hành động logout
    st.components.v1.html(
        """
        <script>
        (function() {
            try {
                const raw = window.parent.localStorage.getItem("examcheat_auth");
                if (raw) {
                    const data = JSON.parse(raw);
                    if (data && data.token) {
                        const target = "/home?auth=" + encodeURIComponent(data.token) +
                            "&role=" + encodeURIComponent(data.role || "") +
                            "&u=" + encodeURIComponent(data.username || "");
                        window.parent.eval("window.location.replace('" + target + "')");
                    }
                }
            } catch (e) {}
        })();
        </script>
        """,
        height=0,
        width=0,
    )

try:
    st.markdown(load_css("styles/login.css"), unsafe_allow_html=True)
except Exception:
    pass

# ── Header Banner ───────────────────────────────────────────
from utils.logo import logo_img

st.markdown(f"""
<div class="login-header">
    <div class="logo-box">
        {logo_img(52, 14)}
    </div>
    <div class="logo-text">ExamCheat AI</div>
    <div class="welcome-title">Chào mừng trở lại</div>
    <div class="welcome-subtitle">Hệ thống giám sát thi thông minh thời gian thực</div>
</div>
""", unsafe_allow_html=True)

# ── Form ────────────────────────────────────────────────────
username = st.text_input("Tên đăng nhập :red[(*)]", placeholder="Nhập tên đăng nhập")
password = st.text_input("Mật khẩu :red[(*)]", type="password", placeholder="Nhập mật khẩu")

login_clicked = st.button("Đăng nhập", type="primary", use_container_width=True)

if login_clicked:
    if not username or not password:
        notify.warning("Vui lòng nhập đầy đủ tên đăng nhập và mật khẩu")
    else:
        with st.spinner("Đang kiểm tra..."):
            res = login(st.session_state.client, username, password)

        if res is None:
            err_txt = "Không kết nối được đến máy chủ hoặc máy chủ không phản hồi (hết thời gian chờ)."
            notify.error(err_txt)
        elif res.status_code == 200:
            data = res.json()
            tok = data.get("access_token")
            role = data.get("role", "teacher")
            st.session_state["access_token_value"] = tok
            st.session_state["refresh_token_value"] = data.get("refresh_token")
            st.session_state["user_role"] = role
            st.session_state["username"] = username
            st.session_state["is_login"] = True

            # Lấy họ tên hiển thị
            try:
                from services.user_api import get_user
                profile = get_user(st.session_state.client)
                if profile:
                    st.session_state["user_fullname"] = profile.get("HoVaTen")
            except Exception:
                pass

            fullname = st.session_state.get("user_fullname") or username

            # Lưu vào localStorage của trình duyệt và điều hướng vào trang chủ
            import json

            auth_json = json.dumps({
                "token": tok,
                "refresh_token": data.get("refresh_token") or "",
                "role": role,
                "username": username,
                "full_name": fullname,
            })
            notify.defer_success(f"Xin chào, {fullname}!")
            st.components.v1.html(
                f"""
                <script>
                try {{
                    window.parent.localStorage.setItem("examcheat_auth", JSON.stringify({auth_json}));
                }} catch (e) {{}}
                window.parent.eval("window.location.replace('/home?auth={tok}&role={role}&u={username}')");
                </script>
                """,
                height=0,
                width=0,
            )
            st.stop()

        elif res.status_code in (401, 403):
            detail_msg = ""
            try:
                detail_msg = str(res.json().get("detail", ""))
            except Exception:
                pass
            if "locked" in detail_msg.lower() or "khóa" in detail_msg.lower():
                err_txt = "Tài khoản của bạn đã bị khóa. Vui lòng liên hệ quản trị viên."
            else:
                err_txt = "Tên đăng nhập hoặc mật khẩu không chính xác. Vui lòng kiểm tra lại."
            notify.error(err_txt)
        else:
            err_txt = f"Lỗi đăng nhập: {res.text}"
            notify.error(err_txt)

# Flush hàng đợi (trang login không có header chung)
flush_toasts()

