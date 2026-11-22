import requests
import streamlit as st

from config import API_BASE_URL
from utils.http import init_session_state

st.set_page_config(layout="wide", initial_sidebar_state="collapsed", page_title="ExamCheat AI")

# ── Khôi phục session & HTTP Client ─────────────────────────
init_session_state()

# ── Validate Session ────────────────────────────────────────
is_login = False

token = st.session_state.get("access_token_value") or st.query_params.get("auth")

if token:
    if not st.session_state.get("access_token_value"):
        st.session_state["access_token_value"] = token
        st.session_state["is_login"] = True
    try:
        res = st.session_state.client.get(
            f"{API_BASE_URL}/users/profile",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5,
        )
        is_login = res.status_code == 200
        if is_login:
            # Lấy vai trò thật từ server thay vì tin query param ?role=
            try:
                _profile = res.json()
                st.session_state["user_role"] = _profile.get("VaiTro") or st.session_state.get("user_role")
                st.session_state["user_fullname"] = (
                    _profile.get("HoVaTen") or st.session_state.get("user_fullname")
                )
            except ValueError:
                pass
    except requests.RequestException:
        is_login = False

# ── Route ───────────────────────────────────────────────────
if is_login:
    # Toàn bộ người dùng đăng nhập điều hướng vào Thi online
    st.switch_page("pages/online_exam.py")
else:
    # Thử khôi phục từ localStorage của trình duyệt trước khi chuyển sang login
    st.components.v1.html(
        """
        <script>
        (function() {
            try {
                const raw = window.parent.localStorage.getItem("examcheat_auth");
                if (raw) {
                    const data = JSON.parse(raw);
                    if (data && data.token) {
                        const landing = "/online_exam";
                        const target = landing + "?auth=" + encodeURIComponent(data.token) +
                            "&role=" + encodeURIComponent(data.role || "") +
                            "&u=" + encodeURIComponent(data.username || "");
                        window.parent.eval("window.location.replace('" + target + "')");
                        return;
                    }
                }
            } catch (e) {}
            window.parent.eval("window.location.replace('/login')");
        })();
        </script>
        """,
        height=0,
        width=0,
    )
    st.stop()
