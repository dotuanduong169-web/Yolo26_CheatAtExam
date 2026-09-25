"""Schema camera cho thiết bị, khởi động và trạng thái luồng.
Logic chính: một camera chỉ chạy một session tại một thời điểm, mở camera mới phải dừng cái cũ.
"""

from typing import Optional

from pydantic import BaseModel


class CameraDevice(BaseModel):
    """Một thiết bị camera khả dụng, index dùng để mở luồng."""

    index: int
    name: str


class CameraListResponse(BaseModel):
    """Danh sách thiết bị camera, count là tổng số tìm thấy."""

    cameras: list[CameraDevice]
    count: int


class CameraStartResponse(BaseModel):
    """Phản hồi khi mở camera, session_id là ca thi vừa tạo."""

    message: str
    session_id: int
    status: str
    user_id: int


class CameraStopResponse(BaseModel):
    """Phản hồi khi dừng camera và chốt ca thi hiện tại."""

    message: str
    status: str
    user_id: int


class CameraInfoResponse(BaseModel):
    """Độ phân giải camera và trạng thái đang chạy."""

    width: int
    height: int
    running: bool


class CameraStatusResponse(BaseModel):
    """Trạng thái camera hiện tại, session_id None nghĩa là không có ca đang chạy."""

    running: bool
    session_id: Optional[int] = None
