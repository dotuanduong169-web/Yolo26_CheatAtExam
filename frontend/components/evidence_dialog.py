"""Component hiển thị chi tiết bằng chứng và xác minh vi phạm (Modal Dialog)."""

import html
import io
from PIL import Image
import streamlit as st

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

    raw_label = data.get("LoaiHanhVi", "?")
    friendly_ai_label = get_friendly_behavior_label(raw_label)
    conf = round(float(data.get("DoTinCay", 0)) * 100, 1)
    status = data.get("TrangThaiKiemTra", "cho_kiem_tra")
    user_label = data.get("NhanNguoiDung")
    time_str = str(data.get("ThoiGianPhatHien", ""))[:19].replace("T", " ")
    bbox = data.get("ToaDo") or []
    evidences = data.get("evidences", [])
    cam_role = data.get("VaiTroCamera") or (
        evidences[0].get("VaiTroCamera") if evidences else None
    ) or "front"
    cam_label = "Camera phụ (điện thoại)" if cam_role == "side" else "Camera trước (webcam)"
    candidate = data.get("candidate") or {}
    session_info = data.get("session") or {}

    stt_text, stt_cls = get_event_status_info(status)

    # Bố cục 2 cột: Ảnh bằng chứng bên trái (1.2) - Thông tin & Nghiệp vụ bên phải (1.0)
    c_left, c_right = st.columns([1.2, 1.0], gap="large")

    with c_left:
        st.markdown(f"""
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <span style="font-size: 13px; font-weight: 600; color: #334155;">📷 {cam_label}</span>
            <span style="font-size: 12px; font-weight: 600; color: #2563eb; background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 12px; padding: 2px 10px;">
                Độ tin cậy: {conf}%
            </span>
        </div>
        """, unsafe_allow_html=True)

        pil_img = None
        if evidences:
            for ev in evidences:
                img_bytes = get_evidence_bytes(client, ev.get("PK_MaBangChung"))
                if not img_bytes:
                    continue
                try:
                    pil_img = Image.open(io.BytesIO(img_bytes))
                except Exception:
                    pil_img = None
                    continue
                st.image(pil_img, use_container_width=True)
                ev_role = ev.get("VaiTroCamera") or cam_role
                ev_cam = "Camera phụ" if ev_role == "side" else "Camera trước"
                st.caption(f"Ảnh bằng chứng · {ev_cam} · {str(ev.get('ThoiGianTao', ''))[:19].replace('T', ' ')}")
                break

        if not pil_img:
            st.info("Chưa có ảnh chụp bằng chứng cho sự kiện này.")

    with c_right:
        # Thông tin thí sinh & ca thi (nếu có)
        if candidate:
            sbd = html.escape(str(candidate.get("SBD") or "—"))
            hoten = html.escape(str(candidate.get("HoTen") or "—"))
            lop = html.escape(str(candidate.get("Lop") or ""))
            lop_str = f" · Lớp {lop}" if lop else ""
            sess_num = session_info.get("parent_session_id") or session_info.get("PK_MaPhienGiamSat") or "—"
            phong = html.escape(str(session_info.get("PhongThi") or "—"))
            mon = html.escape(str(session_info.get("MonThi") or "—"))

            st.markdown(f"""
            <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-left: 3px solid #2563eb; border-radius: 8px; padding: 10px 12px; margin-bottom: 12px;">
                <div style="font-size: 11px; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px;">Thí sinh</div>
                <div style="font-size: 14px; font-weight: 700; color: #1e293b; margin-top: 2px;">
                    {sbd} · {hoten} <span style="font-size: 12px; font-weight: normal; color: #64748b;">{lop_str}</span>
                </div>
                <div style="font-size: 11.5px; color: #64748b; margin-top: 3px;">
                    Ca thi #{sess_num} · Phòng {phong} · {mon}
                </div>
            </div>
            """, unsafe_allow_html=True)

        user_label_disp = get_friendly_behavior_label(user_label) if user_label else "Chưa xác minh"
        if status == "sai":
            user_label_disp = "Bác bỏ (Báo sai)"
        elif status in ("dung", "da_kiem_tra", "da_xac_minh") and not user_label:
            user_label_disp = friendly_ai_label

        st.markdown(f"""
        <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; margin-bottom: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 4px 0; border-bottom: 1px solid #f1f5f9;">
                <span style="font-size: 12.5px; color: #64748b;">Mã sự kiện:</span>
                <span style="font-size: 13px; font-weight: 700; color: #1e293b;">#EV-{event_id:02d}</span>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 4px 0; border-bottom: 1px solid #f1f5f9;">
                <span style="font-size: 12.5px; color: #64748b;">Hành vi phát hiện:</span>
                <span style="font-size: 13px; font-weight: 700; color: var(--wf-danger);">{friendly_ai_label} <small style="color: #94a3b8; font-weight: normal;">({raw_label})</small></span>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 4px 0; border-bottom: 1px solid #f1f5f9;">
                <span style="font-size: 12.5px; color: #64748b;">Thời điểm:</span>
                <span style="font-size: 12.5px; font-weight: 500; color: #475569;">{time_str}</span>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 4px 0; border-bottom: 1px solid #f1f5f9;">
                <span style="font-size: 12.5px; color: #64748b;">Nguồn camera:</span>
                <span style="font-size: 12.5px; font-weight: 600; color: #334155;">{cam_label}</span>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 4px 0;">
                <span style="font-size: 12.5px; color: #64748b;">Trạng thái:</span>
                <span><span class="{stt_cls}">{stt_text}</span></span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<div style='font-size: 13px; font-weight: 700; color: #1e293b; margin-bottom: 6px;'>Xác minh nghiệp vụ</div>", unsafe_allow_html=True)

        is_pending = (status == "cho_kiem_tra")
        if not is_pending:
            if status in ("dung", "da_kiem_tra", "da_xac_minh"):
                confirmed_label = get_friendly_behavior_label(user_label or data.get("NhanAI") or raw_label)
                st.markdown(
                    f"<div style='background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 10px 12px; color: #16a34a; font-size: 13px; font-weight: 600; text-align: center; margin-bottom: 10px;'>"
                    f"✓ Đã xác nhận Vi phạm: {confirmed_label}"
                    f"</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    "<div style='background: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; padding: 10px 12px; color: #dc2626; font-size: 13px; font-weight: 600; text-align: center; margin-bottom: 10px;'>"
                    "✗ Đã bác bỏ sự kiện (Báo sai)"
                    "</div>",
                    unsafe_allow_html=True,
                )
        else:
            available_labels = ["Cheat_Paper", "cellphone", "quay_dau", "quay_sau", "cui_xuong", "vang_mat", "nhieu_nguoi"]
            label_names = {
                "Cheat_Paper": "Tài liệu / Phao thi (Cheat_Paper)",
                "cellphone": "Điện thoại di động (cellphone)",
                "quay_dau": "Quay đầu trao đổi (>45°)",
                "quay_sau": "Quay người về sau",
                "cui_xuong": "Cúi đầu nhìn xuống bàn",
                "vang_mat": "Vắng mặt khỏi khung hình",
                "nhieu_nguoi": "Nhiều người trong khung hình",
            }
            current_choice = user_label if user_label in available_labels else (raw_label if raw_label in available_labels else "Cheat_Paper")
            def_idx = available_labels.index(current_choice) if current_choice in available_labels else 0

            selected_label = st.selectbox(
                "Kết luận / sửa nhãn vi phạm:",
                options=available_labels,
                index=def_idx,
                format_func=lambda x: label_names.get(x, x),
                key=f"modal_sel_label_{event_id}",
            )

            btn_c1, btn_c2 = st.columns(2, gap="small")
            with btn_c1:
                if st.button("Xác nhận Vi phạm", key=f"modal_confirm_{event_id}", type="primary", use_container_width=True):
                    res = verify_event(client, event_id, "dung", selected_label)
                    if res is not None and res.status_code == 200:
                        notify.defer_success(f"Đã xác nhận sự kiện EV-{event_id:02d} là Vi phạm ({label_names.get(selected_label, selected_label)})")
                        st.rerun()
                    else:
                        notify.error("Không thể cập nhật trạng thái sự kiện")

            with btn_c2:
                if st.button("Báo sai (Bác bỏ)", key=f"modal_reject_{event_id}", use_container_width=True):
                    res = verify_event(client, event_id, "sai", "")
                    if res is not None and res.status_code == 200:
                        notify.defer_success(f"Đã bác bỏ sự kiện EV-{event_id:02d} (Báo sai)")
                        st.rerun()
                    else:
                        notify.error("Không thể cập nhật trạng thái sự kiện")


if hasattr(st, "dialog"):
    @st.dialog("Chi tiết sự kiện vi phạm", width="large")
    def show_evidence_dialog(event_id: int):
        render_evidence_content(event_id)
else:
    def show_evidence_dialog(event_id: int):
        with st.expander(f"Chi tiết bằng chứng: EV-{event_id:02d}", expanded=True):
            render_evidence_content(event_id)
