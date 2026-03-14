# --- Vending Machine Central Server (Refactored Version) ---

import os
from flask import Flask, jsonify
from flask_cors import CORS
import logging

# Import hàm khởi tạo DB
from database import create_tables

# Import các Blueprints từ thư mục routes
from routes.users import user_bp
from routes.products import product_bp
from routes.transactions import trans_bp
from routes.devices import device_bp

# --- CẤU HÌNH LOGGING ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Đường dẫn thư mục static (chứa ảnh sản phẩm)
STATIC_FOLDER = os.path.join(os.path.dirname(__file__), 'static')

# Khởi tạo Flask app
app = Flask(__name__, static_folder=STATIC_FOLDER)
CORS(app)

# --- KHỞI TẠO DATABASE ---
# Đảm bảo các bảng được tạo khi app khởi động
try:
    create_tables()
except Exception as e:
    logger.error(f"Failed to initialize database tables: {e}")

# --- ĐĂNG KÝ BLUEPRINTS (ROUTES) ---
app.register_blueprint(user_bp)
app.register_blueprint(product_bp)
app.register_blueprint(trans_bp)
app.register_blueprint(device_bp)

# --- ROUTE CƠ BẢN ---
@app.route('/')
def healthCheck():
    return jsonify({'status': 'OK', 'message': 'Vending Machine Central Server is running'})

# --- KHỞI CHẠY (Dành cho chạy local test, trên Docker sẽ dùng Gunicorn) ---
if __name__ == '__main__':
    logger.info("Server Vending Machine running on port 5000...")
    app.run(host='0.0.0.0', port=5000, debug=False)