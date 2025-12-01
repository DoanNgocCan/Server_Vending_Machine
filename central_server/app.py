# --- START OF FILE app.py (CLEAN VERSION: NO UNITS_LEFT IN MASTER INVENTORY) ---

from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timezone
import json
import os
import sqlite3
import uuid
import threading
import logging

# --- CẤU HÌNH ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), 'central_server.db')
app = Flask(__name__)
CORS(app)
dbLock = threading.Lock()

# --- CÁC HÀM TIỆN ÍCH DATABASE ---
def getDatabaseConnection():
    """Thiết lập kết nối đến CSDL SQLite."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def create_tables():
    """Tạo các bảng CSDL cần thiết."""
    with getDatabaseConnection() as conn:
        cursor = conn.cursor()
        
        # 1. Bảng users
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                full_name TEXT NOT NULL,
                phone_number TEXT UNIQUE NOT NULL,
                birthday TEXT,
                password TEXT NOT NULL,
                points INTEGER DEFAULT 0,
                status TEXT DEFAULT 'active',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # 2. Bảng inventory (MASTER DATA - Đã xóa units_left và reorder_point)
        # Bảng này chỉ chứa thông tin tĩnh của sản phẩm + tổng số đã bán
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_name TEXT UNIQUE NOT NULL,
                price REAL NOT NULL,
                units_sold INTEGER DEFAULT 0,
                cost_price REAL DEFAULT 0,
                description TEXT
            )
        """)

        # 3. Bảng device_inventory (KHO RIÊNG TỪNG MÁY)
        # Đây là nơi duy nhất lưu trữ tồn kho thực tế (units_left)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS device_inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                item_name TEXT NOT NULL,
                units_left INTEGER DEFAULT 0, 
                last_updated TEXT,
                UNIQUE(device_id, item_name)
            )
        """)

        # 4. Bảng transactions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                transaction_id TEXT PRIMARY KEY,
                user_id TEXT,
                device_id TEXT,
                items TEXT,
                total_amount REAL NOT NULL,
                payment_method TEXT,
                payment_status TEXT,
                created_at TEXT NOT NULL,
                paid_at TEXT
            )
        """)
        
        # 5. Bảng giá riêng (Custom Price)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS device_pricing (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                item_name TEXT NOT NULL,
                custom_price REAL,
                custom_cost_price REAL,
                UNIQUE(device_id, item_name)
            )
        """)
        conn.commit()
        logger.info("Database tables checked/created (Clean Version).")

def logSystemEvent(event_type, message, metadata=None):
    logger.info(f"[{event_type.upper()}]: {message} | Metadata: {metadata}")

# --- ROUTE CƠ BẢN ---
@app.route('/')
def healthCheck():
    return jsonify({'status': 'OK', 'message': 'Vending Machine Central Server is running'})

# =============================================================================
# 1. API QUẢN LÝ USER
# =============================================================================

@app.route('/api/users', methods=['GET'])
def listUsers():
    try:
        limit = int(request.args.get('limit', 20))
        offset = int(request.args.get('offset', 0))
        search = request.args.get('search', None)
        
        with dbLock, getDatabaseConnection() as conn:
            base_query = "SELECT user_id, full_name, phone_number, points, birthday, status, created_at FROM users"
            count_query = "SELECT COUNT(*) as total FROM users"
            params = []

            if search:
                where_clause = " WHERE (full_name LIKE ? OR phone_number LIKE ?)"
                base_query += where_clause
                count_query += where_clause
                params.extend([f"%{search}%", f"%{search}%"])

            total_records = conn.execute(count_query, params).fetchone()['total']
            
            base_query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            users = [dict(row) for row in conn.execute(base_query, params).fetchall()]

        return jsonify({'success': True, 'total': total_records, 'users': users})
    except Exception as e:
        logger.error(f"Error /api/users: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/user/register', methods=['POST'])
def registerUser():
    try:
        data = request.get_json()
        required = ['user_id', 'full_name', 'phone_number', 'birthday', 'password']
        if not all(field in data for field in required):
            return jsonify({'success': False, 'message': 'Missing fields'}), 400

        user_id = data['user_id']
        now_iso = datetime.now(timezone.utc).isoformat()
        
        with dbLock, getDatabaseConnection() as conn:
            cursor = conn.cursor()
            if cursor.execute("SELECT 1 FROM users WHERE phone_number = ?", (data['phone_number'],)).fetchone():
                return jsonify({'success': False, 'message': 'Phone exists'}), 409
            if cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,)).fetchone():
                return jsonify({'success': False, 'message': 'ID exists'}), 409
            
            cursor.execute("""
                INSERT INTO users (user_id, full_name, phone_number, birthday, password, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 'active', ?, ?)
            """, (user_id, data['full_name'], data['phone_number'], data['birthday'], data['password'], now_iso, now_iso))
        
        logSystemEvent('user_register', f'Registered {user_id}')
        return jsonify({'success': True, 'user_id': user_id, 'message': 'Success'})
    except Exception as e:
        logger.error(f"Error Register: {e}")
        return jsonify({'success': False}), 500

@app.route('/api/user/login', methods=['POST'])
def loginUser():
    data = request.get_json()
    phone = data.get('phone_number')
    password = data.get('password')
    try:
        with getDatabaseConnection() as conn:
            user = conn.execute("SELECT * FROM users WHERE phone_number = ?", (phone,)).fetchone()
            if user and user['password'] == password:
                return jsonify({'success': True, 'user': dict(user)})
    except Exception: pass
    return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

@app.route('/api/user/<string:user_id>', methods=['GET'])
def get_user_by_id(user_id):
    try:
        with getDatabaseConnection() as conn:
            user = conn.execute("SELECT user_id, full_name, phone_number, points FROM users WHERE user_id = ?", (user_id,)).fetchone()
            if user: return jsonify({'success': True, 'user': dict(user)})
            return jsonify({'success': False}), 404
    except Exception: return jsonify({'success': False}), 500

# =============================================================================
# 2. API SẢN PHẨM & KHO (ĐÃ SỬA - KHÔNG CÒN UNITS_LEFT TRONG INVENTORY)
# =============================================================================

@app.route('/api/products/batch_sync', methods=['POST'])
def batchSyncProducts():
    """
    [FIXED] Đồng bộ sản phẩm:
    - inventory: CHỈ lưu tên, giá, ảnh. (Đã bỏ units_left)
    - device_inventory: Lưu tồn kho của máy.
    """
    try:
        data = request.get_json()
        device_id = request.headers.get('X-Device-ID') or data.get('products', [{}])[0].get('device_id')
        products = data.get('products', [])
        
        if not device_id:
            return jsonify({'success': False, 'message': 'Missing Device ID'}), 400

        now_iso = datetime.now(timezone.utc).isoformat()

        with dbLock, getDatabaseConnection() as conn:
            cursor = conn.cursor()
            count = 0
            
            for p in products:
                name = p.get('name')
                price = p.get('price')
                image = p.get('image', '')
                qty = p.get('quantity', 0) 
                
                # 1. Update MASTER DATA (inventory)
                # ĐÃ XÓA units_left và reorder_point ở đây
                cursor.execute("""
                    INSERT INTO inventory (item_name, price, cost_price, description)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(item_name) DO UPDATE SET
                        price = excluded.price,
                        description = excluded.description
                """, (name, price, price * 0.7, f"Image: {image}"))

                # 2. Update DEVICE INVENTORY (Kho riêng)
                cursor.execute("""
                    INSERT INTO device_inventory (device_id, item_name, units_left, last_updated)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(device_id, item_name) DO UPDATE SET
                        units_left = excluded.units_left,
                        last_updated = excluded.last_updated
                """, (device_id, name, qty, now_iso))
                count += 1
            
            conn.commit()
            
        logSystemEvent('batch_sync', f'Synced {count} items for {device_id}')
        return jsonify({'success': True, 'message': f'Synced {count} items'})
    except Exception as e:
        logger.error(f"Sync Error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/products/set_custom', methods=['POST'])
def setDevicePrice():
    """Admin: Set giá riêng cho máy"""
    try:
        data = request.get_json()
        device_id = data.get('device_id')
        item_name = data.get('item_name')
        price = data.get('price')
        
        with dbLock, getDatabaseConnection() as conn:
            conn.execute("""
                INSERT INTO device_pricing (device_id, item_name, custom_price)
                VALUES (?, ?, ?)
                ON CONFLICT(device_id, item_name) DO UPDATE SET custom_price = excluded.custom_price
            """, (device_id, item_name, price))
            conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/products', methods=['GET'])
def getProducts():
    """
    Client: Lấy danh sách.
    - Nếu có X-Device-ID: Lấy units_left từ device_inventory.
    - Nếu không (Admin): Lấy master data (không có units_left).
    """
    try:
        device_id = request.headers.get('X-Device-ID')
        
        with getDatabaseConnection() as conn:
            conn.row_factory = sqlite3.Row
            
            if device_id:
                # JOIN lấy tồn kho riêng của máy
                query = """
                    SELECT i.item_name, i.price, i.description, 
                           COALESCE(d.units_left, 0) as units_left,
                           dp.custom_price
                    FROM inventory i
                    LEFT JOIN device_inventory d ON i.item_name = d.item_name AND d.device_id = ?
                    LEFT JOIN device_pricing dp ON i.item_name = dp.item_name AND dp.device_id = ?
                """
                rows = conn.execute(query, (device_id, device_id)).fetchall()
            else:
                # Admin/Mặc định: Lấy master data.
                # LƯU Ý: Không còn cột units_left trong inventory nữa
                rows = conn.execute("SELECT * FROM inventory").fetchall()

            final_list = []
            for row in rows:
                p = dict(row)
                if device_id and row.get('custom_price') is not None:
                    p['price'] = row['custom_price']
                p.pop('custom_price', None)
                final_list.append(p)

        return jsonify({'success': True, 'products': final_list})
    except Exception as e:
        logger.error(f"Get Products Error: {e}")
        return jsonify({'success': False}), 500

# =============================================================================
# 3. API GIAO DỊCH
# =============================================================================

@app.route('/api/transactions/record', methods=['POST'])
def recordTransaction():
    try:
        data = request.get_json()
        device_id = request.headers.get('X-Device-ID') or data.get('device_id', 'UNKNOWN')
        
        total_amount = data['total_amount']
        items = data['items']
        customer_info = data.get('customer_info')
        
        with dbLock, getDatabaseConnection() as conn:
            cursor = conn.cursor()
            
            # 1. Lưu transaction
            transaction_id = f"trans_{uuid.uuid4().hex[:10]}"
            items_str = json.dumps(items)
            now_iso = datetime.now(timezone.utc).isoformat()
            user_id = customer_info.get('user_id') if customer_info else None
            
            cursor.execute("""
                INSERT INTO transactions (transaction_id, total_amount, items, user_id, device_id, payment_status, created_at)
                VALUES (?, ?, ?, ?, ?, 'completed', ?)
            """, (transaction_id, total_amount, items_str, user_id, device_id, now_iso))
            
            # 2. Xử lý kho và thống kê
            for item in items:
                p_name = item.get('product_name') or item.get('name')
                qty = item.get('quantity', 1)
                
                if p_name:
                    # A. Trừ kho RIÊNG (device_inventory)
                    cursor.execute("""
                        UPDATE device_inventory 
                        SET units_left = units_left - ? 
                        WHERE item_name = ? AND device_id = ?
                    """, (qty, p_name, device_id))
                    
                    # B. Cộng tổng bán (inventory)
                    cursor.execute("""
                        UPDATE inventory 
                        SET units_sold = units_sold + ? 
                        WHERE item_name = ?
                    """, (qty, p_name))

            # 3. Cập nhật điểm
            if user_id and customer_info:
                new_total = customer_info.get('new_total_points')
                if new_total is not None:
                     cursor.execute("""
                        UPDATE users 
                        SET points = ?, updated_at = ? 
                        WHERE user_id = ?
                     """, (new_total, now_iso, user_id))
            
            conn.commit()

        logSystemEvent('transaction', f'Recorded {transaction_id} from {device_id}')
        return jsonify({'success': True, 'transaction_id': transaction_id})

    except Exception as e:
        logger.error(f"Transaction Error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/transactions', methods=['GET'])
def list_transactions():
    """Admin: Xem lịch sử giao dịch"""
    try:
        limit = int(request.args.get('limit', 20))
        offset = int(request.args.get('offset', 0))
        device_id = request.args.get('device_id')
        user_id = request.args.get('user_id')

        with dbLock, getDatabaseConnection() as conn:
            query = "SELECT * FROM transactions"
            count_query = "SELECT COUNT(*) as total FROM transactions"
            conditions = []
            params = []

            if device_id:
                conditions.append("device_id = ?")
                params.append(device_id)
            if user_id:
                conditions.append("user_id = ?")
                params.append(user_id)

            if conditions:
                clause = " WHERE " + " AND ".join(conditions)
                query += clause
                count_query += clause
            
            total = conn.execute(count_query, params).fetchone()['total']
            
            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            trans = [dict(row) for row in conn.execute(query, params).fetchall()]

        return jsonify({'success': True, 'total': total, 'transactions': trans})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/inventory/stats', methods=['GET'])
def get_inventory_stats():
    """Admin: Xem thống kê bán chạy"""
    try:
        with dbLock, getDatabaseConnection() as conn:
            stats = conn.execute("SELECT item_name, units_sold FROM inventory ORDER BY units_sold DESC").fetchall()
            result = {row['item_name']: row['units_sold'] for row in stats}

        return jsonify({'success': True, 'stats': result})
    except Exception as e:
        return jsonify({'success': False}), 500

# --- KHỞI CHẠY ---
if __name__ == '__main__':
    create_tables()
    print("Server Vending Machine (Full Version with Multi-Client) running on port 5000...")
    app.run(host='0.0.0.0', port=5000, debug=True)