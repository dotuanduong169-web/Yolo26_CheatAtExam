"""Ngoại lệ HTTP chuẩn cho API. Logic: đóng gói sẵn mã lỗi để trả về đồng nhất."""

from fastapi import HTTPException, status


class ValidationError(HTTPException):
    """Lỗi 400 — dữ liệu đầu vào không hợp lệ."""

    def __init__(self, detail: str = "Invalid input"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class AuthenticationError(HTTPException):
    """Lỗi 401 — thiếu hoặc sai xác thực."""

    def __init__(self, detail: str = "Not authenticated"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


class AuthorizationError(HTTPException):
    """Lỗi 403 — không đủ quyền."""

    def __init__(self, detail: str = "Not enough permissions"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class NotFoundError(HTTPException):
    """Lỗi 404 — không tìm thấy tài nguyên."""

    def __init__(self, detail: str = "Resource not found"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class ConflictError(HTTPException):
    """Lỗi 409 — tài nguyên đã tồn tại (VD: trùng email)."""

    def __init__(self, detail: str = "Resource already exists"):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)


class RateLimitError(HTTPException):
    """Lỗi 429 — vượt quá giới hạn số lần gọi."""

    def __init__(self, detail: str = "Too many requests"):
        super().__init__(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=detail)


class InternalServerError(HTTPException):
    """Lỗi 500 — lỗi phía máy chủ."""

    def __init__(self, detail: str = "Internal server error"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
        )
