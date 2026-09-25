"""Schema phản hồi dùng chung cho nhiều endpoint.
Logic chính: tin nhắn chuẩn cho thao tác đơn, gói token cho đăng nhập và làm mới phiên.
"""

from pydantic import BaseModel


class MessageResponse(BaseModel):
    """Phản hồi chuẩn chỉ gồm một thông báo."""

    message: str


class TokenResponse(BaseModel):
    """Gói token sau đăng nhập, refresh_token vắng khi client chỉ dùng cookie."""

    message: str
    user_id: int
    role: str
    access_token: str
    refresh_token: str | None = None
