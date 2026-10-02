"""Hàng tab điều hướng ngang dưới header: luôn thấy, bấm để chuyển trang và trung tâm thông báo hệ thống góc trên bên phải."""

import streamlit as st

TABS = [
    ("home", "Giám sát", "pages/home.py"),
    ("events", "Sự kiện", "pages/events.py"),
    ("statistics", "Thống kê", "pages/statistics.py"),
    ("history", "Lịch sử", "pages/history.py"),
    ("devices", "Thiết bị", "pages/devices.py"),
    ("setting", "Cài đặt", "pages/setting.py"),
]


def render_nav_tabs(active: str = "home") -> None:
    """Vẽ hàng tab ngang điều hướng duy nhất.
    Góc trên bên phải tích hợp Trung tâm thông báo hệ thống và Nút đăng xuất.
    """
    notif_data = st.session_state.get("system_notifications") or {}
    unread_alerts = notif_data.get("total_pending", 0)
    alerts_list = notif_data.get("alerts", [])
    active_sess = notif_data.get("active_session")
    server_time = notif_data.get("server_time") or "Đang đồng bộ"

    notif_label = f"Thông báo ({unread_alerts})" if unread_alerts > 0 else "Thông báo"

    # Bố cục hàng tab điều hướng và cụm thông báo góc phải
    cols = st.columns([1, 1, 1, 1, 1, 1, 1.4, 1])

    # 6 Tab điều hướng chính
    for i, (key, label, target) in enumerate(TABS):
        with cols[i]:
            if key == active:
                st.markdown(
                    f"<div class='nav-tab-active'>{label}</div>",
                    unsafe_allow_html=True,
                )
            elif st.button(label, key=f"navtab_{key}", use_container_width=True):
                st.switch_page(target)

    # Cột góc phải 1: Trung tâm thông báo hệ thống (Popover)
    with cols[6]:
        with st.popover(notif_label, use_container_width=True):
            st.markdown("""
            <div style="font-weight: 700; font-size: 15px; margin-bottom: 6px; color: #1e293b;">
                Trung tâm Thông báo Hệ thống
            </div>
            <div style="font-size: 12px; color: #64748b; margin-bottom: 12px; border-bottom: 1px solid #e2e8f0; padding-bottom: 6px;">
                Cập nhật tự động theo thời gian thực
            </div>
            """, unsafe_allow_html=True)

            # Tình trạng kết nối máy chủ
            st.markdown(f"""
            <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px 12px; margin-bottom: 12px; font-size: 12.5px;">
                <div style="display:flex; justify-content:space-between; margin-bottom: 4px;">
                    <span style="color: #64748b;">Trạng thái máy chủ:</span>
                    <strong style="color: #16a34a;">Trực tuyến</strong>
                </div>
                <div style="display:flex; justify-content:space-between; margin-bottom: 4px;">
                    <span style="color: #64748b;">Mô hình AI:</span>
                    <strong style="color: #2563eb;">YOLO26-Edge (Sẵn sàng)</strong>
                </div>
                <div style="display:flex; justify-content:space-between;">
                    <span style="color: #64748b;">Giờ máy chủ:</span>
                    <span style="color: #334155; font-family: monospace;">{server_time}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Ca thi đang hoạt động
            if active_sess:
                room_txt = active_sess.get("room", "Phòng thi")
                sub_txt = active_sess.get("subject", "Môn thi")
                sid_txt = active_sess.get("session_id", "")
                st.markdown(f"""
                <div style="background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px; padding: 10px 12px; margin-bottom: 12px; font-size: 12.5px;">
                    <div style="font-weight: 600; color: #1d4ed8; margin-bottom: 2px;">Ca thi đang giám sát #{sid_txt}</div>
                    <div style="color: #1e40af;">Phòng: <strong>{room_txt}</strong> | Môn: <strong>{sub_txt}</strong></div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div style="background: #f1f5f9; border: 1px solid #e2e8f0; border-radius: 8px; padding: 8px 12px; margin-bottom: 12px; font-size: 12px; color: #64748b;">
                    Hiện chưa có ca thi nào đang diễn ra.
                </div>
                """, unsafe_allow_html=True)

            # Danh sách cảnh báo vi phạm mới nhất
            st.markdown(f"<div style='font-size: 13px; font-weight: 600; margin-bottom: 8px;'>Vi phạm chờ xác minh ({unread_alerts}):</div>", unsafe_allow_html=True)

            if not alerts_list:
                st.markdown("""
                <div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 10px 12px; text-align: center; color: #15803d; font-size: 12px; margin-bottom: 12px;">
                    Không có cảnh báo vi phạm mới. Phòng thi an toàn.
                </div>
                """, unsafe_allow_html=True)
            else:
                for alert in alerts_list:
                    a_id = alert.get("id")
                    b_lbl = alert.get("behavior_label", "Nghi vấn vi phạm")
                    conf = alert.get("confidence", 0)
                    t_str = alert.get("detected_at", "")[-8:]
                    s_id = alert.get("session_id")
                    st.markdown(f"""
                    <div style="border-left: 3px solid #dc2626; background: #fff5f5; padding: 6px 10px; border-radius: 0 6px 6px 0; margin-bottom: 6px; font-size: 12px;">
                        <div style="display:flex; justify-content:space-between;">
                            <strong style="color: #b91c1c;">EV-{a_id:02d} | {b_lbl}</strong>
                            <span style="color: #dc2626; font-weight: 600;">{conf}%</span>
                        </div>
                        <div style="color: #64748b; font-size: 11px; margin-top: 2px;">
                            Ca #{s_id} | Lúc {t_str} | Chờ kiểm tra
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

            st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)

            # Nút điều hướng nhanh
            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                if st.button("Xem sự kiện", key="notif_to_events_btn", use_container_width=True):
                    st.switch_page("pages/events.py")
            with btn_col2:
                if st.button("Làm mới", key="notif_refresh_btn", use_container_width=True):
                    st.rerun()

    # Cột góc phải 2: Nút Đăng xuất
    with cols[7]:
        if st.button("Đăng xuất", key="navtab_logout", use_container_width=True, help="Đăng xuất khỏi hệ thống"):
            try:
                from services.auth_api import logout
                if "client" in st.session_state:
                    logout(st.session_state.client)
            except Exception:
                pass
            st.session_state["access_token_value"] = None
            st.session_state["is_login"] = False
            if "auth" in st.query_params:
                del st.query_params["auth"]
            st.switch_page("pages/login.py")

    st.markdown(
        """
        <style>
        .nav-tab-active {
            text-align: center;
            padding: 8px 4px;
            border-radius: 8px;
            background-color: #1677ff;
            color: white;
            font-weight: 600;
            font-size: 13.5px;
            letter-spacing: -0.2px;
            box-shadow: 0 2px 6px rgba(22, 119, 255, 0.25);
        }
        div[data-testid="stButton"] > button {
            border-radius: 8px !important;
            font-size: 13px !important;
            font-weight: 500 !important;
        }
        div[data-testid="stPopover"] > button {
            border-radius: 8px !important;
            font-size: 13px !important;
            font-weight: 600 !important;
            background-color: #f8fafc !important;
            border: 1px solid #cbd5e1 !important;
            color: #1e293b !important;
            transition: all 0.2s ease !important;
        }
        div[data-testid="stPopover"] > button:hover {
            border-color: #94a3b8 !important;
            background-color: #f1f5f9 !important;
        }
        button[key="navtab_logout"] {
            color: #ef4444 !important;
            border-color: #fecaca !important;
        }
        button[key="navtab_logout"]:hover {
            background-color: #fef2f2 !important;
            border-color: #ef4444 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )



