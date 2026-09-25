"""Thanh điều hướng chung: menu chuyển trang và đăng xuất.
Luồng chính: vẽ 4 nút menu -> tô sáng mục đang mở bằng CSS -> xử lý đăng xuất."""

import streamlit as st
from services.auth_api import logout

def render_sidebar(active: str = "home") -> None:
    """Vẽ thanh bên với menu điều hướng và nút đăng xuất.
    Dùng CSS theo vị trí nút để tô sáng đúng mục đang mở."""
    with st.sidebar:
        # Khoảng đệm trên cùng để tránh dính header
        st.markdown('<div style="height: 10px;"></div>', unsafe_allow_html=True)
        
        # Các nút điều hướng
        # Chú ý: thứ tự tại đây phải khớp chỉ số trong CSS bên dưới
        btn_home = st.button("🎥 Giám sát", key="nav_home", use_container_width=True)
        btn_stats = st.button("📊 Thống kê", key="nav_statistics", use_container_width=True)
        btn_hist = st.button("🕘 Lịch sử", key="nav_history", use_container_width=True)
        btn_settings = st.button("⚙️ Cài đặt", key="nav_setting", use_container_width=True)

        # Xử lý chuyển trang khi nhấn nút
        if btn_home: st.switch_page("pages/home.py")
        if btn_stats: st.switch_page("pages/statistics.py")
        if btn_hist: st.switch_page("pages/history.py")
        if btn_settings: st.switch_page("pages/setting.py")

        # Đổi tên mục đang mở thành chỉ số nút (bắt đầu từ 1)
        # Dùng nth-of-type(n+2) vì phía trên có một khối đệm
        menu_map = {"home": 1, "statistics": 2, "history": 3, "setting": 4}
        active_idx = menu_map.get(active, 1)

        # Bơm CSS động để tô sáng nút đang mở
        st.markdown(f"""
        <style>
        /* Nhắm vào nút thứ N trong sidebar để tô sáng mục đang mở */
        /* Mỗi st.button được bọc trong div[data-testid="stButton"] */
        section[data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div:nth-child({active_idx + 1}) button {{
            background-color: #1677ff !important;
            color: white !important;
            font-weight: 600 !important;
            box-shadow: 0 4px 12px rgba(22, 119, 255, 0.2) !important;
        }}
        
        /* Giữ chữ và biểu tượng màu trắng khi đang mở */
        section[data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div:nth-child({active_idx + 1}) button p {{
            color: white !important;
        }}
        </style>
        """, unsafe_allow_html=True)

        # Nút đăng xuất
        # CSS trong header.css sẽ đẩy nút này xuống đáy sidebar
        if st.button("↪️ Đăng xuất", key="logout_btn", use_container_width=True):
            try:
                if "client" in st.session_state:
                    logout(st.session_state.client)
            except Exception:
                pass
            st.session_state.clear()
            st.switch_page("pages/login.py")