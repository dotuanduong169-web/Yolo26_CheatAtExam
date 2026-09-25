"""Giới hạn số lần thử theo IP chống dò mật khẩu. Logic: cửa sổ trượt theo IP, singleton an toàn luồng."""

import threading
from datetime import datetime, timedelta, timezone

from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """
    Bộ giới hạn số lần thử theo ngưỡng và cửa sổ thời gian.

    Logic: singleton dùng chung, mọi truy cập qua cùng một thể hiện.
    """

    _instance = None
    _lock = threading.Lock()

    MAX_ATTEMPTS: int = settings.RATE_LIMIT_MAX_ATTEMPTS
    TIME_WINDOW: timedelta = timedelta(minutes=settings.RATE_LIMIT_WINDOW_MINUTES)

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._attempts: dict[str, list[datetime]] = {}
        return cls._instance

    # ── Nội bộ ────────────────────────────────────────────

    def _clean_expired(self, ip: str) -> None:
        """Xóa lượt thử quá hạn của IP. Logic: giữ lại mốc trong cửa sổ, rỗng thì xóa IP."""
        if ip not in self._attempts:
            return

        cutoff = datetime.now(timezone.utc) - self.TIME_WINDOW
        self._attempts[ip] = [t for t in self._attempts[ip] if t > cutoff]

        if not self._attempts[ip]:
            del self._attempts[ip]

    # ── API công khai ──────────────────────────────────────────

    def is_rate_limited(self, ip: str) -> bool:
        """Trả True khi IP đã hết lượt. Logic: dọn mốc cũ rồi so với ngưỡng."""
        self._clean_expired(ip)
        return len(self._attempts.get(ip, [])) >= self.MAX_ATTEMPTS

    def record_attempt(self, ip: str) -> None:
        """Ghi một lượt thử thất bại của IP."""
        self._attempts.setdefault(ip, []).append(datetime.now(timezone.utc))
        logger.debug(
            f"Rate-limit: attempt recorded for {ip} "
            f"({len(self._attempts[ip])}/{self.MAX_ATTEMPTS})"
        )

    def get_remaining_attempts(self, ip: str) -> int:
        """Trả số lượt còn lại của IP. Logic: không bao giờ âm."""
        self._clean_expired(ip)
        return max(0, self.MAX_ATTEMPTS - len(self._attempts.get(ip, [])))

    def get_reset_time(self, ip: str) -> datetime:
        """Trả thời điểm cửa sổ reset của IP. Logic: mốc cũ nhất cộng độ dài cửa sổ."""
        attempts = self._attempts.get(ip, [])
        if not attempts:
            return datetime.now(timezone.utc)
        return min(attempts) + self.TIME_WINDOW

    def reset_for_ip(self, ip: str) -> None:
        """Xóa toàn bộ lượt theo dõi của IP (VD: đăng nhập đúng)."""
        if self._attempts.pop(ip, None):
            logger.info(f"Rate-limit reset for IP: {ip}")

    def reset_all(self) -> None:
        """Xóa toàn bộ dữ liệu theo dõi giới hạn."""
        self._attempts.clear()
        logger.info("All rate limits reset")

    def get_stats(self) -> dict:
        """Trả số liệu chẩn đoán giới hạn."""
        return {
            "tracked_ips": len(self._attempts),
            "total_attempts": sum(len(v) for v in self._attempts.values()),
            "max_attempts": self.MAX_ATTEMPTS,
            "time_window_minutes": int(self.TIME_WINDOW.total_seconds() / 60),
        }
