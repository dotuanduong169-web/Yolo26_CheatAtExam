"""Trang Quản lý Tài khoản (FR01): Danh sách người dùng, phân quyền Admin/Giám thị và cài đặt hồ sơ cá nhân."""

import streamlit as st
from utils.notify import notify

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
from utils.http import auth_query_params, init_session_state
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


@st.dialog("Tạo tài khoản người dùng mới")
def create_user_dialog():
    tc1, tc2 = st.columns(2)
    with tc1:
        new_username = st.text_input("Tên đăng nhập", placeholder="VD: gv_le_ngoc_an")
        new_fullname = st.text_input("Họ và tên", placeholder="VD: ThS. Lê Ngọc An")
    with tc2:
        new_password = st.text_input("Mật khẩu ban đầu", type="password", placeholder="Tối thiểu 6 ký tự, 1 hoa, 1 số")
        new_role = st.selectbox("Vai trò phân quyền", ["teacher", "admin"], format_func=lambda x: "Cán bộ coi thi (teacher)" if x == "teacher" else "Quản trị viên (admin)")

    st.caption("Quy chuẩn an toàn mật khẩu: Tối thiểu 6 ký tự, chứa ít nhất 1 chữ in hoa (A-Z) và 1 chữ số (0-9).")
    msg_slot = st.empty()
    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Hủy bỏ", use_container_width=True):
            st.rerun()
    with c2:
        if st.button("Tạo tài khoản", type="primary", use_container_width=True):
            if not new_username.strip() or not new_fullname.strip() or not new_password.strip():
                with msg_slot:
                    notify.inline_warning("Vui lòng nhập đầy đủ các trường thông tin.")
            else:
                is_valid, errors = validate_password_rules(new_password)
                if not is_valid:
                    with msg_slot:
                        notify.inline_error(f"Mật khẩu chưa đạt tiêu chuẩn an toàn: Thiếu {', '.join(errors)}.")
                else:
                    ok, res = admin_create_user(client, new_username.strip(), new_fullname.strip(), new_password, new_role)
                    if ok:
                        notify.defer_success("Đã tạo tài khoản thành công!")
                        st.rerun()
                    else:
                        with msg_slot:
                            notify.inline_error(f"{res}")


@st.dialog("Chỉnh sửa thông tin người dùng")
def edit_user_name_dialog(u_id: int, cur_name: str, cur_role: str, cur_status: str):
    edit_full_name = st.text_input("Họ và tên người dùng", value=cur_name)
    msg_slot = st.empty()
    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Hủy bỏ", use_container_width=True):
            st.rerun()
    with c2:
        if st.button("Lưu thay đổi", type="primary", use_container_width=True):
            if not edit_full_name.strip():
                with msg_slot:
                    notify.inline_warning("Họ tên không được để trống")
            else:
                ok, res = admin_update_user(client, u_id, cur_role, cur_status, ho_va_ten=edit_full_name.strip())
                if ok:
                    notify.defer_success("Đã cập nhật họ tên thành công!")
                    st.rerun()
                else:
                    with msg_slot:
                        notify.inline_error("Lỗi khi cập nhật thông tin")


tab_users, tab_profile = st.tabs(["Danh sách người dùng", "Hồ sơ cá nhân"])

# ── Xử lý query params thao tác người dùng (từ link icon SVG) ──
if "toggle_role" in st.query_params:
    try:
        t_uid = int(st.query_params["toggle_role"])
        cur_role = st.query_params.get("cur_role", "teacher")
        cur_stt = st.query_params.get("cur_stt", "hoat_dong")
        user_login = st.query_params.get("user_login", f"user_{t_uid}")
        del st.query_params["toggle_role"]
        for p in ["cur_role", "cur_stt", "user_login"]:
            if p in st.query_params:
                del st.query_params[p]
        new_role = "teacher" if cur_role == "admin" else "admin"
        ok, res = admin_update_user(client, t_uid, new_role, cur_stt)
        if ok:
            notify.defer_success(f"Đã đổi vai trò cho @{user_login}")
            st.rerun()
        else:
            notify.error("Lỗi khi cập nhật vai trò")
    except Exception:
        pass

if "toggle_status" in st.query_params:
    try:
        s_uid = int(st.query_params["toggle_status"])
        cur_role = st.query_params.get("cur_role", "teacher")
        cur_stt = st.query_params.get("cur_stt", "hoat_dong")
        user_login = st.query_params.get("user_login", f"user_{s_uid}")
        del st.query_params["toggle_status"]
        for p in ["cur_role", "cur_stt", "user_login"]:
            if p in st.query_params:
                del st.query_params[p]
        new_status = "khoa" if cur_stt == "hoat_dong" else "hoat_dong"
        ok, res = admin_update_user(client, s_uid, cur_role, new_status)
        if ok:
            notify.defer_success(f"Đã cập nhật trạng thái @{user_login}")
            st.rerun()
        else:
            notify.error("Lỗi khi đổi trạng thái tài khoản")
    except Exception:
        pass

# =========================================================================
# TAB 1: DANH SÁCH NGƯỜI DÙNG & PHÂN QUYỀN (CHỈ ADMIN HOẶC XEM QUYỀN)
# =========================================================================
with tab_users:
    if not is_admin:
        notify.inline(
            "Tính năng phân quyền và quản trị danh sách người dùng dành riêng cho Quản trị viên (Admin). Bạn đang đăng nhập với vai trò Cán bộ coi thi, vui lòng chuyển sang tab 'Hồ sơ cá nhân & Đổi mật khẩu' để xem và cập nhật thông tin của bạn.",
            kind="warning",
            title="Quyền truy cập bị giới hạn"
        )
    else:
        users = list_all_users(client)

        if "edit_user" in st.query_params:
            try:
                eu_id = int(st.query_params["edit_user"])
                del st.query_params["edit_user"]
                m_user = next((u for u in users if u.get("PK_MaNguoiDung") == eu_id), None)
                if m_user:
                    edit_user_name_dialog(
                        eu_id,
                        m_user.get("HoVaTen", ""),
                        m_user.get("VaiTro", "teacher"),
                        m_user.get("TrangThai", "hoat_dong"),
                    )
            except Exception:
                pass

        uh_col1, uh_col2 = st.columns([3.2, 1])
        with uh_col1:
            st.markdown(f"""
            <div class="wf-box" style="margin-bottom: 0;">
                <div class="wf-box-header">
                    <div class="wf-box-title">Danh sách người dùng & phân quyền</div>
                    <span class="wf-badge danger">Tổng tài khoản: {len(users)}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

        with uh_col2:
            if st.button("+ Thêm tài khoản mới", type="primary", use_container_width=True):
                create_user_dialog()

        if not users:
            notify.empty_state("Không có dữ liệu người dùng", "Chưa có tài khoản nào được ghi nhận trong cơ sở dữ liệu.")
        else:
            # Header hàng bảng
            th1, th2, th3, th4, th5, th6 = st.columns([0.8, 1.6, 2.0, 1.6, 1.0, 1.8])
            th1.caption("MÃ ND")
            th2.caption("TÊN ĐĂNG NHẬP")
            th3.caption("HỌ VÀ TÊN")
            th4.caption("VAI TRÒ")
            th5.caption("TRẠNG THÁI")
            th6.markdown('<div style="text-align:right; font-size:11.5px; font-weight:700; color:#64748b; letter-spacing:0.5px;">THAO TÁC</div>', unsafe_allow_html=True)

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
                        st.markdown(f"<strong>{u_name}</strong>", unsafe_allow_html=True)
                    with c4:
                        st.markdown(role_badge, unsafe_allow_html=True)
                    with c5:
                        st.markdown(status_badge, unsafe_allow_html=True)
                    with c6:
                        new_role = "teacher" if u_role == "admin" else "admin"
                        role_tooltip = "Hạ xuống Cán bộ coi thi" if u_role == "admin" else "Nâng quyền Quản trị viên"
                        new_status = "khoa" if u_status == "hoat_dong" else "hoat_dong"
                        lock_tooltip = "Tạm khóa tài khoản" if u_status == "hoat_dong" else "Kích hoạt lại tài khoản"
                        lock_cls = "lock-btn" if u_status == "hoat_dong" else "unlock-btn"

                        u_c1, u_c2, u_c3 = st.columns([1, 1, 1])
                        with u_c1:
                            if st.button(" ", key=f"btn_act_role_u_{u_id}", help=role_tooltip):
                                ok, res = admin_update_user(client, u_id, new_role, u_status)
                                if ok:
                                    notify.defer_success(f"Đã đổi vai trò cho @{u_login}")
                                else:
                                    notify.error("Lỗi khi cập nhật vai trò")
                                st.rerun()
                        with u_c2:
                            if st.button(" ", key=f"btn_act_edit_u_{u_id}", help="Chỉnh sửa họ tên người dùng"):
                                edit_user_name_dialog(u_id, u_name, u_role, u_status)
                        with u_c3:
                            lock_key = f"btn_act_{'lock' if u_status == 'hoat_dong' else 'unlock'}_u_{u_id}"
                            if st.button(" ", key=lock_key, help=lock_tooltip):
                                ok, res = admin_update_user(client, u_id, u_role, new_status)
                                if ok:
                                    notify.defer_success(f"Đã cập nhật trạng thái @{u_login}")
                                else:
                                    notify.error("Lỗi khi cập nhật trạng thái")
                                st.rerun()

                    st.markdown("<hr style='margin: 4px 0 8px 0; border: none; border-top: 1px solid var(--wf-border);'>", unsafe_allow_html=True)



# =========================================================================
# TAB 2: HỒ SƠ CÁ NHÂN & BẢO MẬT
# =========================================================================
with tab_profile:
    user = get_user(client)
    if not user:
        notify.warning("Không thể tải thông tin tài khoản hiện tại.")
    else:
        full_name = user.get("HoVaTen", "")
        username = user.get("TenDangNhap", "")
        role = user.get("VaiTro", "teacher")
        first_letter = full_name.strip()[:1].upper() if full_name.strip() else username[:1].upper()

        col_profile_card, col_security_card = st.columns([1, 1], gap="medium")

        # Cột 1: Thông tin hồ sơ
        with col_profile_card:
            my_role_badge = get_user_role_badge(role)
            st.markdown(f"""
            <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.03); height: 100%;">
                <div style="display: flex; align-items: center; gap: 14px; margin-bottom: 20px; padding-bottom: 14px; border-bottom: 1px solid #f1f5f9;">
                    <div style="width: 48px; height: 48px; border-radius: 50%; background: #eff6ff; color: #2563eb; display: flex; align-items: center; justify-content: center; font-size: 20px; font-weight: 700; border: 2px solid #bfdbfe;">
                        {first_letter}
                    </div>
                    <div>
                        <div style="font-size: 16px; font-weight: 700; color: #0f172a;">{full_name}</div>
                        <div style="font-size: 12px; color: #64748b; margin-top: 2px;">
                            <span style="background: #f1f5f9; padding: 2px 8px; border-radius: 10px; font-family: monospace;">@{username}</span>
                            <span style="margin-left: 6px;">{my_role_badge}</span>
                        </div>
                    </div>
                </div>
                <div style="font-size: 13.5px; font-weight: 600; color: #334155; margin-bottom: 12px;">Cập nhật thông tin cá nhân</div>
            </div>
            """, unsafe_allow_html=True)

            new_name_val = st.text_input("Họ và tên hiển thị", value=full_name, key="profile_fullname_input")
            if st.button("Lưu thay đổi họ tên", type="primary", use_container_width=True, key="btn_save_profile_name"):
                if not new_name_val.strip():
                    notify.inline_warning("Họ tên không được để trống")
                else:
                    ok, res = update_user(client, new_name_val.strip())
                    if ok:
                        st.session_state["user_fullname"] = new_name_val.strip()
                        notify.defer_success("Đã cập nhật họ tên thành công!")
                        st.rerun()
                    else:
                        notify.inline_error("Lỗi khi cập nhật thông tin")

        # Cột 2: Bảo mật & Đổi mật khẩu
        with col_security_card:
            st.markdown("""
            <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 20px 20px 10px 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
                <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 16px; padding-bottom: 14px; border-bottom: 1px solid #f1f5f9;">
                    <div style="width: 36px; height: 36px; border-radius: 8px; background: #fef2f2; color: #dc2626; display: flex; align-items: center; justify-content: center;">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
                            <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
                        </svg>
                    </div>
                    <div>
                        <div style="font-size: 15px; font-weight: 700; color: #0f172a;">Bảo mật & Đổi mật khẩu</div>
                        <div style="font-size: 12px; color: #64748b;">Quản lý mật khẩu đăng nhập tài khoản</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            old_p = st.text_input("Mật khẩu hiện tại :red[(*)]", type="password", key="sec_old_pass")
            new_p = st.text_input("Mật khẩu mới :red[(*)]", type="password", help="Tối thiểu 6 ký tự, ít nhất 1 chữ hoa và 1 chữ số", key="sec_new_pass")
            confirm_p = st.text_input("Xác nhận mật khẩu mới :red[(*)]", type="password", key="sec_confirm_pass")

            st.markdown("""
            <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 8px 12px; margin: 10px 0; font-size: 12px; color: #64748b; display: flex; align-items: center; gap: 8px;">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0;">
                    <circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>
                </svg>
                <span>Yêu cầu an toàn: Tối thiểu 6 ký tự, có ít nhất 1 chữ cái in hoa (A-Z) và 1 chữ số (0-9).</span>
            </div>
            """, unsafe_allow_html=True)

            if st.button("Cập nhật mật khẩu", type="primary", use_container_width=True, key="btn_update_password"):
                if not old_p or not new_p or not confirm_p:
                    notify.warning("Vui lòng điền đầy đủ tất cả các trường mật khẩu.")
                elif new_p != confirm_p:
                    notify.error("Mật khẩu xác nhận không khớp với mật khẩu mới.")
                else:
                    is_valid, errors = validate_password_rules(new_p)
                    if not is_valid:
                        notify.error(f"Mật khẩu mới không hợp lệ: Cần bổ sung {', '.join(errors)}.")
                    else:
                        ok, res = change_password(client, old_p, new_p)
                        if ok:
                            notify.success("Đổi mật khẩu thành công! Mật khẩu mới đã được lưu.")
                        else:
                            notify.inline_error(f"{res}")

