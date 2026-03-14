import os

# Flask server URL (sẽ được override bởi biến môi trường API_URL trong Docker)
SERVER_URL = os.environ.get("API_URL", "http://localhost:5000")

# Thời gian timeout cho API calls (giây)
API_TIMEOUT = 15

# Debug mode
DEBUG = os.environ.get("DEBUG", "false").lower() == "true"

# Giới hạn kích thước ảnh upload (5MB)
MAX_IMAGE_SIZE = 5 * 1024 * 1024

# Định dạng ảnh được phép upload
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}

# Số sản phẩm mỗi trang
PAGINATION_SIZE = 20

# Thông tin đăng nhập Admin (nên lấy từ .env trong production)
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")
