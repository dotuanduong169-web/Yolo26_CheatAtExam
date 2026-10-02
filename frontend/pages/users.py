"""Trang Quản lý Tài khoản (FR01): Danh sách người dùng, phân quyền Admin/Giám thị và cài đặt hồ sơ cá nhân."""

import streamlit as st

from services.user_api import (
    admin_create_user,
    admin_update_user,
    change_password,
    get_user,
    list_all_users,
    update_user,
)
from utils.auth_guard import require_auth
from utils.hide_streamlit_sidebar import hide_sidebar
from utils.http import init_session_state
from utils.load_css import load_css
from utils.render_header import render_page_header
from utils.status_helpers import get_user_role_badge, get_user_status_badge

# ── Cấu hình trang ──────────────────────────────────────────
st.set_page_config(layout="wide", initial_sidebar_state="collapsed", page_title="Quản lý người dùng")

init_session_state()
require_auth()

# ── Styles & Sidebar ────────────────────────────────────────
hide_sidebar()
st.markdown(load_css("styles/sidebar.css"), unsafe_allow_html=True)
st.markdown(load_css("styles/app_theme.css"), unsafe_allow_html=True)
render_page_header("Quản lý người dùng", active="setting")

client = st.session_state.client
is_admin = st.session_state.get("user_role") == "admin"


def validate_password_rules(pwd: str) -> tuple[bool, list[str]]:
    """Kiểm tra quy chuẩn mật khẩu: tối thiểu 6 ký tự, có ít nhất 1 chữ in hoa và 1 chữ số."""
    errors = []
    if len(pwd) < 6:
        errors.append("Tối thiểu 6 ký tự")
    if not any(c.isupper() for c in pwd):
        errors.append("Ít nhất 1 chữ in hoa (A-Z)")
    if not any(c.isdigit() for c in pwd):
        errors.append("Ít nhất 1 chữ số (0-9)")
    return len(errors) == 0, errors


tab_users, tab_profile = st.tabs(["Danh sách người dùng & Phân quyền", "Hồ sơ cá nhân & Đổi mật khẩu"])

# =========================================================================
# TAB 1: DANH SÁCH NGƯỜI DÙNG & PHÂN QUYỀN (CHỈ ADMIN HOẶC XEM QUYỀN)
# =========================================================================
with tab_users:
    if not is_admin:
        st.info("Tính năng phân quyền và quản trị danh sách người dùng dành riêng cho Quản trị viên (Admin). Bạn đang đăng nhập với vai trò Cán bộ coi thi.")
    else:
        users = list_all_users(client)

        st.markdown(f"""
        <div class="wf-box">
            <div class="wf-box-header">
                <div class="wf-box-title">Danh sách người dùng & phân quyền</div>
                <span class="wf-badge danger">Tổng tài khoản: {len(users)}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if not users:
            st.info("Không có dữ liệu người dùng.")
        else:
            # Header hàng bảng
            th1, th2, th3, th4, th5, th6 = st.columns([0.8, 1.6, 2.0, 1.6, 1.0, 1.8])
            th1.caption("MÃ ND")
            th2.caption("TÊN ĐĂNG NHẬP")
            th3.caption("HỌ VÀ TÊN")
            th4.caption("VAI TRÒ")
            th5.caption("TRẠNG THÁI")
            th6.caption("HÀNH ĐỘNG")

            st.markdown("<hr style='margin: 4px 0 8px 0; border: none; border-top: 1px solid var(--wf-border);'>", unsafe_allow_html=True)

            for u in users:
                u_id = u.get("PK_MaNguoiDung")
                u_login = u.get("TenDangNhap")
                u_name = u.get("HoVaTen")
                u_role = u.get("VaiTro")
                u_status = u.get("TrangThai", "hoat_dong")

                role_badge = get_user_role_badge(u_role)
                status_badge = get_user_status_badge(u_status)

                with st.container():
                    c1, c2, c3, c4, c5, c6 = st.columns([0.8, 1.6, 2.0, 1.6, 1.0, 1.8])
                    with c1:
                        st.markdown(f"<strong>USR-{u_id:02d}</strong>", unsafe_allow_html=True)
                    with c2:
                        st.markdown(f"<code>{u_login}</code>", unsafe_allow_html=True)
                    with c3:
                        st.markdown(f"<strong>{u_name}</strong>")
                    with c4:
                        st.markdown(role_badge, unsafe_allow_html=True)
                    with c5:
                        st.markdown(status_badge, unsafe_allow_html=True)
                    with c6:
                        # 3 Nút nghiệp vụ tiếng Việt: Đổi quyền, Sửa họ tên, Khóa/Mở
                        col_u1, col_u2, col_u3 = st.columns(3)
                        with col_u1:
                            new_role = "teacher" if u_role == "admin" else "admin"
                            role_tooltip = "Hạ xuống Cán bộ coi thi" if u_role == "admin" else "Nâng quyền Quản trị viên"
                            if st.button("Đổi quyền", key=f"role_btn_{u_id}", help=role_tooltip):
                                ok, res = admin_update_user(client, u_id, new_role, u_status)
                                if ok:
                                    st.toast(f"Đã đổi vai trò cho @{u_login}")
                                    st.rerun()
                                else:
                                    st.error("Lỗi khi cập nhật vai trò")
                        with col_u2:
                            if st.button("Sửa", key=f"edit_u_btn_{u_id}", help="Chỉnh sửa thông tin tài khoản"):
                                st.session_state[f"editing_user_{u_id}"] = not st.session_state.get(f"editing_user_{u_id}", False)
                        with col_u3:
                            new_status = "khoa" if u_status == "hoat_dong" else "hoat_dong"
                            lock_tooltip = "Tạm khóa tài khoản" if u_status == "hoat_dong" else "Kích hoạt lại tài khoản"
                            lock_label = "Khóa" if u_status == "hoat_dong" else "Mở"
                            if st.button(lock_label, key=f"lock_btn_{u_id}", help=lock_tooltip):
                                ok, res = admin_update_user(client, u_id, u_role, new_status)
                                if ok:
                                    st.toast(f"Đã cập nhật trạng thái @{u_login}")
                                    st.rerun()
                                else:
                                    st.error("Lỗi khi đổi trạng thái tài khoản")

                    # Form inline sửa tên người dùng
                    if st.session_state.get(f"editing_user_{u_id}", False):
                        with st.container():
                            st.markdown("<div style='background: #f8fafc; padding: 10px 14px; border-radius: 6px; margin: 8px 0;'>", unsafe_allow_html=True)
                            eu1, eu2 = st.columns([2.5, 1])
                            with eu1:
                                edit_full_name = st.text_input("Họ và tên", value=u_name, key=f"eu_name_{u_id}")
                            with eu2:
                                st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                                if st.button("Lưu họ tên", key=f"save_eu_{u_id}", type="primary"):
                                    ok, res = admin_update_user(client, u_id, u_role, u_status, ho_va_ten=edit_full_name.strip())
                                    if ok:
                                        st.session_state[f"editing_user_{u_id}"] = False
                                        st.toast("Đã cập nhật họ tên thành công")
                                        st.rerun()
                            st.markdown("</div>", unsafe_allow_html=True)

                    st.markdown("<hr style='margin: 4px 0 8px 0; border: none; border-top: 1px solid var(--wf-border);'>", unsafe_allow_html=True)

        # Form tạo tài khoản mới
        with st.expander("Tạo tài khoản người dùng mới", expanded=False):
            tc1, tc2 = st.columns(2)
            with tc1:
                new_username = st.text_input("Tên đăng nhập", placeholder="VD: gv_le_ngoc_an")
                new_fullname = st.text_input("Họ và tên", placeholder="VD: ThS. Lê Ngọc An")
            with tc2:
                new_password = st.text_input("Mật khẩu ban đầu", type="password", placeholder="Tối thiểu 6 ký tự, 1 chữ hoa, 1 số")
                new_role = st.selectbox("Vai trò phân quyền", ["teacher", "admin"], format_func=lambda x: "Cán bộ coi thi (teacher)" if x == "teacher" else "Quản trị viên (admin)")

            st.caption("Quy chuẩn an toàn mật khẩu: Tối thiểu 6 ký tự, chứa ít nhất 1 chữ in hoa (A-Z) và ít nhất 1 chữ số (0-9).")

            if st.button("Tạo tài khoản", type="primary"):
                if not new_username or not new_fullname or not new_password:
                    st.warning("Vui lòng nhập đầy đủ các trường thông tin.")
                else:
                    is_valid, errors = validate_password_rules(new_password)
                    if not is_valid:
                        st.error(f"Mật khẩu chưa đạt tiêu chuẩn an toàn: Thiếu {', '.join(errors)}.")
                    else:
                        ok, res = admin_create_user(client, new_username.strip(), new_fullname.strip(), new_password, new_role)
                        if ok:
                            st.toast("Đã tạo tài khoản thành công!")
                            st.rerun()
                        else:
                            st.error(f"{res}")


# =========================================================================
# TAB 2: HỒ SƠ CÁ NHÂN & BẢO MẬT
# =========================================================================
with tab_profile:
    user = get_user(client)
    if not user:
        st.warning("Không thể tải thông tin tài khoản hiện tại.")
    else:
        full_name = user.get("HoVaTen", "")
        username = user.get("TenDangNhap", "")
        role = user.get("VaiTro", "teacher")

        st.markdown("""
        <div class="wf-box">
            <div class="wf-box-header">
                <div class="wf-box-title">Thông tin hồ sơ cá nhân</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        col_p1, col_p2 = st.columns([1, 2])
        with col_p1:
            my_role_badge = get_user_role_badge(role)
            st.markdown(f"""
            <div style="font-size: 13px; line-height: 2;">
                <div>Tên đăng nhập: <strong>@{username}</strong></div>
                <div>Vai trò hiện tại: {my_role_badge}</div>
            </div>
            """, unsafe_allow_html=True)

        with col_p2:
            new_name_val = st.text_input("Họ và tên hiển thị", value=full_name)
            if st.button("Lưu thay đổi họ tên", type="primary"):
                if not new_name_val.strip():
                    st.warning("Họ tên không được để trống")
                else:
                    ok, res = update_user(client, new_name_val.strip())
                    if ok:
                        st.session_state["user_fullname"] = new_name_val.strip()
                        st.toast("Đã cập nhật họ tên!")
                        st.rerun()
                    else:
                        st.error("Lỗi khi cập nhật")

        st.markdown("<hr style='margin: 20px 0;'>", unsafe_allow_html=True)

        st.markdown("""
        <div class="wf-box">
            <div class="wf-box-header">
                <div class="wf-box-title">Bảo mật & Đổi mật khẩu</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        pw1, pw2, pw3 = st.columns(3)
        with pw1:
            old_p = st.text_input("Mật khẩu hiện tại", type="password")
        with pw2:
            new_p = st.text_input("Mật khẩu mới", type="password", help="Tối thiểu 6 ký tự, ít nhất 1 chữ hoa và 1 chữ số")
        with pw3:
            confirm_p = st.text_input("Xác nhận mật khẩu mới", type="password")

        st.caption("Tiêu chuẩn mật khẩu an toàn: Tối thiểu 6 ký tự, phải có ít nhất 1 chữ cái in hoa (A-Z) và ít nhất 1 chữ số (0-9).")

        if st.button("Cập nhật mật khẩu", type="secondary"):
            if not old_p or not new_p or not confirm_p:
                st.warning("Vui lòng điền đầy đủ tất cả các trường mật khẩu.")
            elif new_p != confirm_p:
                st.error("Mật khẩu xác nhận không khớp với mật khẩu mới.")
            else:
                is_valid, errors = validate_password_rules(new_p)
                if not is_valid:
                    st.error(f"Mật khẩu mới không hợp lệ: Cần bổ sung {', '.join(errors)}.")
                else:
                    ok, res = change_password(client, old_p, new_p)
                    if ok:
                        st.toast("Đổi mật khẩu thành công! Mật khẩu mới đã được lưu.")
                    else:
                        st.error(f"{res}")

