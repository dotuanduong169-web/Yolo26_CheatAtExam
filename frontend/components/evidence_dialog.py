"""Component hiển thị chi tiết bằng chứng và xác minh vi phạm (Anti-AI Neutral Wireframe style)."""

import base64
import io
import streamlit as st
from PIL import Image

from services.event_api import get_event_detail, get_evidence_bytes, verify_event
from utils.notify import notify
from utils.status_helpers import get_event_status_info, get_friendly_behavior_label


def render_evidence_content(event_id: int):
    """Vẽ nội dung bằng chứng và trường xác minh lại nhãn đúng (NhanNguoiDung)."""
    client = st.session_state.client
    data = get_event_detail(client, event_id)
    if not data:
        st.error(f"Không tìm thấy thông tin sự kiện #{event_id}")
        return

    label = data.get("LoaiHanhVi", "?")
    friendly_ai_label = get_friendly_behavior_label(label)
    conf = round(float(data.get("DoTinCay", 0)) * 100, 1)
    status = data.get("TrangThaiKiemTra", "cho_kiem_tra")
    user_label = data.get("NhanNguoiDung")
    time_str = str(data.get("ThoiGianPhatHien", ""))[:19]
    bbox = data.get("ToaDo") or []
    evidences = data.get("evidences", [])

    stt_text, stt_cls = get_event_status_info(status)

    c_left, c_right = st.columns([1.2, 1], gap="medium")

    with c_left:
        st.caption("Ảnh chụp camera bằng chứng:")
        img_bytes = None
        if evidences:
            img_bytes = get_evidence_bytes(client, evidences[0].get("PK_MaBangChung"))

        if img_bytes:
            try:
                pil_img = Image.open(io.BytesIO(img_bytes))
                st.image(pil_img, use_container_width=True)
            except Exception:
                st.warning("Không thể hiển thị ảnh bằng chứng")
        else:
            st.info("Chưa có snapshot cho sự kiện này")

    with c_right:
        user_label_disp = get_friendly_behavior_label(user_label) if user_label else "Chưa xác minh"
        st.markdown(f"""
        <div style="font-size: 13px; line-height: 1.8;">
            <div>Mã sự kiện: <strong>EV-{event_id:02d}</strong></div>
            <div>Nhãn AI phát hiện: <strong style="color: var(--wf-danger);">{friendly_ai_label} ({label})</strong></div>
            <div>Độ tin cậy AI: <strong>{conf}%</strong></div>
            <div>Thời điểm: <span>{time_str}</span></div>
            <div>Nhãn đã xác minh: <strong>{user_label_disp}</strong></div>
            <div>Trạng thái hiện tại: <span class="{stt_cls}">{stt_text}</span></div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)

        # Trường xác minh lại nhãn đúng (NhanNguoiDung)
        available_labels = ["Cheat_Paper", "cellphone", "quay_dau", "quay_sau", "cui_xuong", "vang_mat", "nhieu_nguoi", "Answer_paper"]
        label_names = {
            "Cheat_Paper": "Tài liệu giấy (Cheat_Paper)",
            "cellphone": "Điện thoại di động (cellphone)",
            "quay_dau": "Quay đầu (>45°)",
            "quay_sau": "Quay người về sau",
            "cui_xuong": "Cúi đầu nhìn xuống gầm bàn",
            "vang_mat": "Vắng mặt khỏi khung hình (vang_mat)",
            "nhieu_nguoi": "Nhiều người trong khung hình (nhieu_nguoi)",
            "Answer_paper": "Giấy thi hợp lệ (Answer_paper - Không vi phạm)",
        }
        current_choice = user_label if user_label in available_labels else (data.get("NhanAI") if data.get("NhanAI") in available_labels else "Cheat_Paper")
        def_idx = available_labels.index(current_choice) if current_choice in available_labels else 0

        selected_label = st.selectbox(
            "Xác minh lại nhãn đúng (NhanNguoiDung):",
            options=available_labels,
            index=def_idx,
            format_func=lambda x: label_names.get(x, x),
            key=f"sel_label_{event_id}",
        )

        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        btn_c1, btn_c2 = st.columns(2)

        with btn_c1:
            if st.button("Bác bỏ (Báo sai)", key=f"reject_{event_id}", use_container_width=True):
                st.session_state["history_active_tab"] = "events"
                st.query_params["tab"] = "events"
                res = verify_event(client, event_id, "sai", "Answer_paper")
                if res is not None and res.status_code == 200:
                    notify.success(f"Đã bác bỏ sự kiện EV-{event_id:02d} (Giấy thi hợp lệ)")
                    st.rerun()
                else:
                    notify.error("Không thể cập nhật trạng thái sự kiện")

        with btn_c2:
            if st.button("Xác nhận Vi phạm", key=f"confirm_{event_id}", type="primary", use_container_width=True):
                st.session_state["history_active_tab"] = "events"
                st.query_params["tab"] = "events"
                res = verify_event(client, event_id, "dung", selected_label)
                if res is not None and res.status_code == 200:
                    notify.success(f"Đã xác nhận sự kiện EV-{event_id:02d} với nhãn: {selected_label}")
                    st.rerun()
                else:
                    notify.error("Không thể cập nhật trạng thái sự kiện")


# Dùng Streamlit dialog nếu hỗ trợ, ngược lại dùng fallback
if hasattr(st, "dialog"):
    @st.dialog("Chi tiết bằng chứng vi phạm")
    def show_evidence_dialog(event_id: int):
        render_evidence_content(event_id)
else:
    def show_evidence_dialog(event_id: int):
        with st.expander(f"Chi tiết bằng chứng: EV-{event_id:02d}", expanded=True):
            render_evidence_content(event_id)
