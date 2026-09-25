"""Danh sách đen token khi đăng xuất. Logic: lưu RAM tới hết hạn tự nhiên, production thay bằng Redis."""

from datetime import datetime, timezone


class TokenBlacklist:
    """Giữ token đã thu hồi. Logic: chỉ giữ tới khi token hết hạn tự nhiên."""

    _blacklist: set[str] = set()
    _expiry_times: dict[str, datetime] = {}

    @classmethod
    def add(cls, token: str, expires_at: datetime) -> None:
        """Thêm token vào danh sách đen kèm hạn dùng."""
        cls._blacklist.add(token)
        cls._expiry_times[token] = expires_at

    @classmethod
    def is_blacklisted(cls, token: str) -> bool:
        """Kiểm tra token đã bị thu hồi chưa. Logic: quá hạn tự nhiên thì tự xóa và coi như sạch."""
        if token not in cls._blacklist:
            return False

        # Tự dọn token đã hết hạn tự nhiên
        expiry = cls._expiry_times.get(token)
        if expiry and datetime.now(timezone.utc) > expiry:
            cls._blacklist.discard(token)
            cls._expiry_times.pop(token, None)
            return False

        return True

    @classmethod
    def clear_expired(cls) -> None:
        """Xóa mọi token đã hết hạn tự nhiên khỏi danh sách đen."""
        now = datetime.now(timezone.utc)
        expired = [t for t, exp in cls._expiry_times.items() if now > exp]
        for token in expired:
            cls._blacklist.discard(token)
            cls._expiry_times.pop(token, None)
