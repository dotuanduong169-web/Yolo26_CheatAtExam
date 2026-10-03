"""Bảo vệ trang: chưa đăng nhập thì chuyển về login."""

import requests
import streamlit as st

from config import API_BASE_URL


def require_auth() -> None:
    """Kiểm tra token còn hiệu lực, tự động làm mới qua refresh_token để chống đá ra ngoài đột ngột."""
    if "client" not in st.session_state:
        st.session_state.client = requests.Session()

    token = st.session_state.get("access_token_value") or st.query_params.get("auth")
    if not token:
        st.switch_page("pages/login.py")
        st.stop()

    # Đồng bộ token từ URL vào session (F5 reload mất session_state nhưng còn query_params)
    if not st.session_state.get("access_token_value"):
        st.session_state["access_token_value"] = token
        if st.query_params.get("role"):
            st.session_state["user_role"] = st.query_params.get("role")
        if st.query_params.get("u"):
            st.session_state["username"] = st.query_params.get("u")
    # Khôi phục refresh token vào cookie client để tự gia hạn sau reload
    if st.query_params.get("refresh"):
        st.session_state["refresh_token_value"] = st.query_params.get("refresh")
        try:
            st.session_state.client.cookies.set("refresh_token", st.query_params.get("refresh"))
        except Exception:
            pass

    # Bỏ qua xác thực backend với token demo
    if str(token).startswith("demo_token"):
        return

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

            # Chỉ đăng xuất khi cả refresh token cũng hết hạn
            st.session_state["access_token_value"] = None
            for _k in ("auth", "refresh"):
                if _k in st.query_params:
                    del st.query_params[_k]
            st.warning("Phiên làm việc đã hết hạn. Vui lòng đăng nhập lại.")
            st.switch_page("pages/login.py")
            st.stop()

    except requests.RequestException:
        # Lỗi mạng tạm thời hoặc server lag, không đá văng người dùng ra sảnh đăng nhập
        pass

