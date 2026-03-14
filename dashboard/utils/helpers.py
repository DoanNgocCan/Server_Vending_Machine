"""
Helper functions - Các hàm tiện ích dùng chung.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import datetime
import pytz
from config import MAX_IMAGE_SIZE

VN_TZ = pytz.timezone("Asia/Ho_Chi_Minh")


def format_currency(amount) -> str:
    """Định dạng tiền tệ VNĐ."""
    try:
        return f"{float(amount):,.0f} ₫"
    except (TypeError, ValueError):
        return "0 ₫"


def format_number(num) -> str:
    """Định dạng số ngắn gọn."""
    try:
        num = float(num)
        if num >= 1_000_000:
            return f"{num / 1_000_000:.1f}M"
        if num >= 1_000:
            return f"{num / 1_000:.1f}K"
        return f"{num:,.0f}"
    except (TypeError, ValueError):
        return "0"


def format_datetime(dt_str) -> str:
    """Chuyển ISO string sang định dạng đọc được."""
    if not dt_str:
        return "—"
    try:
        dt = datetime.fromisoformat(str(dt_str).replace("Z", "+00:00"))
        dt_vn = dt.astimezone(VN_TZ)
        return dt_vn.strftime("%H:%M %d/%m/%Y")
    except Exception:
        return str(dt_str)


def validate_image_file(uploaded_file, max_size_bytes=MAX_IMAGE_SIZE) -> tuple[bool, str]:
    """
    Kiểm tra file ảnh hợp lệ.
    Trả về (is_valid, error_message).
    """
    if uploaded_file is None:
        return False, "Chưa chọn file"

    allowed = {"jpg", "jpeg", "png", "webp"}
    ext = uploaded_file.name.rsplit(".", 1)[-1].lower() if "." in uploaded_file.name else ""
    if ext not in allowed:
        return False, f"Định dạng không hỗ trợ. Chỉ chấp nhận: {', '.join(allowed)}"

    if uploaded_file.size > max_size_bytes:
        return False, f"File quá lớn. Tối đa {max_size_bytes // (1024*1024)}MB"

    return True, ""


def stock_status_color(units_left: int) -> str:
    """Trả về màu HTML theo mức tồn kho."""
    if units_left <= 0:
        return "🔴"
    if units_left < 5:
        return "🟠"
    if units_left < 10:
        return "🟡"
    return "🟢"
