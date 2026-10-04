"""Logo hệ thống dùng chung: đọc 1 lần từ frontend/assets, nhúng base64 vào HTML."""

import base64
from functools import lru_cache
from pathlib import Path

_LOGO_PATHS = (
    Path(__file__).resolve().parents[1] / "assets" / "cheat_exam_logo.png",
    Path("frontend/assets/cheat_exam_logo.png"),
    Path("assets/cheat_exam_logo.png"),
)


@lru_cache(maxsize=1)
def _logo_b64() -> str:
    """Đọc file logo, thu về 256px rồi mã hóa base64, cache để không đọc đĩa mỗi lần render."""
    import io

    for p in _LOGO_PATHS:
        if p.is_file():
            raw = p.read_bytes()
            try:
                from PIL import Image

                img = Image.open(io.BytesIO(raw)).convert("RGB")
                img.thumbnail((256, 256))
                buf = io.BytesIO()
                img.save(buf, format="PNG", optimize=True)
                raw = buf.getvalue()
            except Exception:
                pass
            return base64.b64encode(raw).decode("ascii")
    return ""


def logo_img(size: int = 36, radius: int = 8) -> str:
    """Trả thẻ <img> logo. Không tìm thấy file thì trả chuỗi rỗng."""
    b64 = _logo_b64()
    if not b64:
        return ""
    return (
        f'<img src="data:image/png;base64,{b64}" width="{size}" height="{size}" '
        f'style="border-radius:{radius}px;display:block;object-fit:cover;" alt="ExamCheat AI"/>'
    )
