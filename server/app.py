# --- Vending Machine Central Server ---

import logging

from flask import Flask, jsonify
from flask_cors import CORS

from database import create_tables
from routes.users import users_bp
from routes.products import products_bp
from routes.transactions import transactions_bp

# --- CẤU HÌNH ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

app = Flask(__name__)
CORS(app)

# --- ĐĂNG KÝ BLUEPRINTS ---
app.register_blueprint(users_bp)
app.register_blueprint(products_bp)
app.register_blueprint(transactions_bp)

# --- ROUTE CƠ BẢN ---
@app.route('/')
def healthCheck():
    return jsonify({'status': 'OK', 'message': 'Vending Machine Central Server is running'})


create_tables()

# --- KHỞI CHẠY ---
if __name__ == '__main__':
    print("Server Vending Machine running on port 5000...")
    app.run(host='0.0.0.0', port=5000, debug=False)
