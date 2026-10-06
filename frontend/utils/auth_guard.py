"""Bảo vệ trang: chưa đăng nhập thì chuyển về login."""

import requests
import streamlit as st

from config import API_BASE_URL


def require_auth() -> None:
    """Kiểm tra token còn hiệu lực, tự động khôi phục từ localStorage khi reload (F5)."""
    if "client" not in st.session_state:
        st.session_state.client = requests.Session()

    token = st.session_state.get("access_token_value") or st.query_params.get("auth")
    if not token:
        # F5 hoặc mở trang mới: thử khôi phục từ localStorage của trình duyệt trước khi đá về login
        st.components.v1.html(
            """
            <script>
            (function() {
                try {
                    const raw = window.parent.localStorage.getItem("examcheat_auth");
                    if (raw) {
                        const data = JSON.parse(raw);
                        if (data && data.token) {
                            const cur = new URL(window.parent.location.href);
                            cur.searchParams.set("auth", data.token);
                            if (data.role) cur.searchParams.set("role", data.role);
                            if (data.username) cur.searchParams.set("u", data.username);
                            window.parent.eval("window.location.replace('" + cur.pathname + cur.search + "')");
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

    # Đồng bộ token từ URL vào session (F5 reload mất session_state nhưng khôi phục qua localStorage)
    if not st.session_state.get("access_token_value"):
        st.session_state["access_token_value"] = token
        st.session_state["is_login"] = True
        if st.query_params.get("role"):
            st.session_state["user_role"] = st.query_params.get("role")
        if st.query_params.get("u"):
            st.session_state["username"] = st.query_params.get("u")
            st.session_state["user_fullname"] = st.query_params.get("u")
    # Khôi phục refresh token vào cookie client để tự gia hạn sau reload
    if st.query_params.get("refresh"):
        st.session_state["refresh_token_value"] = st.query_params.get("refresh")
        try:
            st.session_state.client.cookies.set("refresh_token", st.query_params.get("refresh"))
        except Exception:
            pass

    # Tự động dọn sạch token khỏi query params và thanh địa chỉ trình duyệt
    if "auth" in st.query_params:
        for k in ("auth", "role", "u", "refresh"):
            if k in st.query_params:
                try:
                    del st.query_params[k]
                except Exception:
                    pass

    st.markdown(
        """
        <script>
        (function() {
            try {
                if (window.location.search && (window.location.search.indexOf("auth=") >= 0 || window.location.search.indexOf("token=") >= 0)) {
                    var cur = new URL(window.location.href);
                    cur.searchParams.delete("auth");
                    cur.searchParams.delete("role");
                    cur.searchParams.delete("u");
                    cur.searchParams.delete("refresh");
                    var cleanUrl = cur.pathname + (cur.search && cur.search !== "?" ? cur.search : "");
                    window.history.replaceState({}, document.title, cleanUrl);
                }
            } catch (e) {}
        })();
        </script>
        """,
        unsafe_allow_html=True,
    )


    try:
        from utils.http import get_auth_headers

        res = st.session_state.client.get(
            f"{API_BASE_URL}/users/profile",
            headers=get_auth_headers(),
            timeout=4,
        )
        if res.status_code == 200:
            return

        # Khi access token hết hạn (401), tự động gọi refresh_token thay vì đá ra login ngay
        if res.status_code == 401:
            from services.auth_api import refresh_token
            ref_res = refresh_token(st.session_state.client)
            if ref_res and ref_res.status_code == 200:
                data = ref_res.json()
                new_token = data.get("access_token")
                if new_token:
                    st.session_state["access_token_value"] = new_token
                    st.query_params["auth"] = new_token
                    return

            # Chỉ đăng xuất khi cả refresh token cũng hết hạn: xoá localStorage và đá về login
            st.session_state["access_token_value"] = None
            st.session_state["is_login"] = False
            for _k in ("auth", "refresh", "role", "u"):
                if _k in st.query_params:
                    del st.query_params[_k]
            st.warning("Phiên làm việc đã hết hạn. Vui lòng đăng nhập lại.")
            st.components.v1.html(
                """
                <script>
                try {
                    window.parent.localStorage.removeItem("examcheat_auth");
                } catch (e) {}
                window.parent.eval("window.location.replace('/login')");
                </script>
                """,
                height=0,
                width=0,
            )
            st.stop()

    except requests.RequestException:
        # Lỗi mạng tạm thời hoặc server lag, không đá văng người dùng ra sảnh đăng nhập
        pass


