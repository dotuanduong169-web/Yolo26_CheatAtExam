"""Endpoint kết quả AI cho sửa nhãn phát hiện thủ công.
Logic chính: user_label do người sửa ưu tiên hơn ai_label và kích hoạt tính lại thống kê frame.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.dependencies import get_current_user
from models.user import User
from database.database import get_db
from schemas.ai_result import AIResultUpdate, AIResultUpdateResponse
from service.frame_service import update_result_label

router = APIRouter(prefix="/ai-result", tags=["AI Result"])


@router.patch("/{result_id}", response_model=AIResultUpdateResponse)
def update_ai_result(
    result_id: int,
    payload: AIResultUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Sửa nhãn một vật phát hiện. Nhãn người dùng chốt đè lên nhãn AI rồi đồng bộ thống kê."""
    return update_result_label(db, result_id, payload.status)
