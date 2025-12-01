# --- START OF FILE app.py (TINH GỌN CHO PROJECT MÁY BÁN HÀNG) ---

from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timezone
import json
import os
import sqlite3
import uuid
import threading
import logging

# --- CÀI ĐẶT ---
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
    """Tạo các bảng CSDL cần thiết cho project."""
    with getDatabaseConnection() as conn:
        cursor = conn.cursor()
        # Bảng users
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
        # Bảng products
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_name TEXT UNIQUE NOT NULL,
                price REAL NOT NULL,
                units_sold INTEGER DEFAULT 0,
                units_left INTEGER DEFAULT 0,
                cost_price REAL DEFAULT 0,
                reorder_point INTEGER DEFAULT 5,
                description TEXT,
                slot_number INTEGER -- Giữ lại để mapping với khay hàng vật lý
            )
        """)
        # Bảng transactions
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
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS device_pricing (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                item_name TEXT NOT NULL,
                custom_price REAL,
                custom_cost_price REAL,
                UNIQUE(device_id, item_name) -- Một máy chỉ có 1 giá cho 1 món
            )
        """)
        conn.commit()
        logger.info("Database tables for Vending Machine checked/created successfully.")

def populate_initial_products():
    """Chèn dữ liệu sản phẩm mẫu vào bảng inventory."""
    # Định dạng: (Tên, Giá bán, Giá vốn, Tồn kho)
    PRODUCT_DATA = [
    ]
    
    with dbLock, getDatabaseConnection() as conn:
        try:
            # Kiểm tra bảng inventory có dữ liệu chưa
            if conn.execute("SELECT COUNT(*) FROM inventory").fetchone()[0] > 0:
                logger.info("Inventory table already has data, skipping population.")
                return
            
            logger.info("Populating sample inventory...")
            for index, (name, price, cost, stock) in enumerate(PRODUCT_DATA, start=1):
                conn.execute("""
                    INSERT INTO inventory 
                    (item_name, price, cost_price, units_left, slot_number, description, reorder_point) 
                    VALUES (?, ?, ?, ?, ?, 'Sản phẩm mẫu', 10)
                """, (name, price, cost, stock, index))
            
            conn.commit()
            logger.info(f"Successfully inserted {len(PRODUCT_DATA)} items into inventory.")
        except Exception as e:
            logger.error(f"Error populating inventory: {e}")

def logSystemEvent(event_type, message, metadata=None):
    logger.info(f"[{event_type.upper()}]: {message} | Metadata: {metadata}")

# --- ROUTE CƠ BẢN ---
@app.route('/')
def healthCheck():
    return jsonify({'status': 'OK', 'message': 'Vending Machine Central Server is running'})

# =============================================================================
# ENDPOINTS QUẢN LÝ USER
# =============================================================================
@app.route('/api/users', methods=['GET'])
def listUsers():
    """
    Lấy danh sách tất cả khách hàng đã đăng ký.
    Hỗ trợ tìm kiếm và phân trang qua query parameters.
    - /api/users -> Lấy 20 user đầu tiên.
    - /api/users?limit=50&offset=50 -> Lấy 50 user, bỏ qua 50 user đầu.
    - /api/users?search=John -> Tìm user có tên hoặc SĐT chứa "John".
    """
    try:
        # Lấy các tham số từ URL, có giá trị mặc định
        limit = int(request.args.get('limit', 20))
        offset = int(request.args.get('offset', 0))
        search = request.args.get('search', None)
        
        # Đảm bảo limit hợp lệ
        if limit < 1:
            limit = 20

        with dbLock, getDatabaseConnection() as conn:
            # Xây dựng câu lệnh query động và an toàn
            base_query = "SELECT user_id, full_name, phone_number, points, birthday, status, created_at FROM users"
            count_query = "SELECT COUNT(*) as total FROM users"
            params = []

            if search:
                search_pattern = f"%{search}%"
                where_clause = " WHERE (full_name LIKE ? OR phone_number LIKE ?)"
                base_query += where_clause
                count_query += where_clause
                params.extend([search_pattern, search_pattern])

            # 1. Lấy tổng số bản ghi khớp với tìm kiếm (quan trọng cho phân trang)
            total_records = conn.execute(count_query, params).fetchone()['total']
            
            # 2. Thêm sắp xếp và phân trang vào câu query chính
            base_query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            # 3. Lấy danh sách user cho trang hiện tại
            users = [dict(row) for row in conn.execute(base_query, params).fetchall()]

        return jsonify({
            'success': True, 
            'total': total_records, 
            'users': users
        })
    except Exception as e:
        logger.error(f"Error in /api/users: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'Internal Server Error'}), 500


@app.route('/api/user/register', methods=['POST'])
def registerUser():
    try:
        data = request.get_json()
        
        # <<< THAY ĐỔI 1: Thêm 'user_id' vào danh sách trường bắt buộc >>>
        required = ['user_id', 'full_name', 'phone_number', 'birthday', 'password']
        if not all(field in data for field in required):
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400

        # <<< THAY ĐỔI 2: Lấy user_id từ dữ liệu client gửi lên >>>
        user_id = data['user_id']
        full_name = data['full_name']
        phone_number = data['phone_number']
        birthday = data['birthday']
        password = data['password']
        
        # <<< THAY ĐỔI 3: Xóa dòng tự tạo user_id >>>
        # Dòng này đã được xóa: user_id = f"user_{uuid.uuid4().hex[:8]}"
        
        now_iso = datetime.now(timezone.utc).isoformat()
        
        with dbLock, getDatabaseConnection() as conn:
            cursor = conn.cursor()

            # <<< CẢI TIẾN: Kiểm tra cả SĐT và user_id tồn tại trước khi INSERT >>>
            # Điều này giúp trả về thông báo lỗi rõ ràng hơn
            cursor.execute("SELECT 1 FROM users WHERE phone_number = ?", (phone_number,))
            if cursor.fetchone():
                return jsonify({'success': False, 'message': 'Phone number already exists'}), 409

            cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
            if cursor.fetchone():
                return jsonify({'success': False, 'message': 'User ID already exists'}), 409
            
            # Sử dụng các biến đã lấy từ 'data'
            cursor.execute("""
                INSERT INTO users (user_id, full_name, phone_number, birthday, password, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 'active', ?, ?)
            """, (user_id, full_name, phone_number, birthday, password, now_iso, now_iso))
            
            # conn.commit() sẽ được gọi tự động khi thoát khỏi 'with' block
        
        logSystemEvent('user_registered', f'New user registered: {user_id} from client')
        # Trả về user_id đã nhận để xác nhận
        return jsonify({'success': True, 'user_id': user_id, 'message': 'User registered successfully using client-provided ID'})

    except Exception as e:
        logger.error(f"Error in /api/user/register: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'Internal Server Error'}), 500
    
def calculate_points_earned(amount):
    """
    Hàm helper để tính điểm nhận được từ một giao dịch.
    Quy tắc: 1000 VNĐ = 1 điểm.
    """
    return int(amount / 1000)

@app.route('/api/user/<string:user_id>', methods=['GET'])
def get_user_by_id(user_id):
    try:
        with getDatabaseConnection() as conn:
            user = conn.execute("SELECT user_id, full_name, phone_number, points FROM users WHERE user_id = ?", (user_id,)).fetchone()
        
        if user:
            return jsonify({'success': True, 'user': dict(user)})
        else:
            return jsonify({'success': False, 'message': 'User not found'}), 404
    except Exception as e:
        logger.error(f"Error getting user by ID: {e}")
        return jsonify({'success': False, 'message': 'Internal Server Error'}), 500

# =============================================================================
# ENDPOINT QUẢN LÝ SẢN PHẨM
# =============================================================================

# Trong app.py -> thay thế API getProducts cũ
# Trong app.py (Thêm mới)
@app.route('/api/products/batch_sync', methods=['POST'])
def batchSyncProducts():
    """
    API nhận danh sách sản phẩm từ Client gửi lên để lưu vào DB Server.
    """
    try:
        data = request.get_json()
        products = data.get('products', [])
        
        if not products:
            return jsonify({'success': False, 'message': 'No products provided'}), 400

        with dbLock, getDatabaseConnection() as conn:
            cursor = conn.cursor()
            count = 0
            
            for p in products:
                name = p.get('name')
                price = p.get('price')
                image = p.get('image', '')
                
                # Tự động tính giá vốn = 70% giá bán (hoặc 0 nếu không muốn set)
                cost = price * 0.7
                
                # Dùng UPSERT: Nếu có rồi thì update giá/mô tả, chưa có thì thêm mới
                cursor.execute("""
                    INSERT INTO inventory (item_name, price, cost_price, units_left, description, reorder_point)
                    VALUES (?, ?, ?, 100, ?, 10)
                    ON CONFLICT(item_name) DO UPDATE SET
                        price = excluded.price,
                        description = excluded.description
                """, (name, price, cost, f"Image: {image}"))
                count += 1
            
            conn.commit()
            
        logSystemEvent('batch_sync', f'Synced {count} products from client.')
        return jsonify({'success': True, 'message': f'Synced {count} items successfully'})

    except Exception as e:
        logger.error(f"Error in batch sync: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
@app.route('/api/products/set_custom', methods=['POST'])
def setDevicePrice():
    """
    API để set giá riêng cho một máy cụ thể.
    Body: { "device_id": "MAY_SAN_BAY", "item_name": "Aquafina", "price": 20000 }
    """
    try:
        data = request.get_json()
        device_id = data.get('device_id')
        item_name = data.get('item_name')
        price = data.get('price')           # Có thể null nếu chỉ muốn sửa giá vốn
        cost_price = data.get('cost_price') # Có thể null
        
        if not device_id or not item_name:
            return jsonify({'success': False, 'message': 'Missing device_id or item_name'}), 400

        with dbLock, getDatabaseConnection() as conn:
            # Dùng INSERT OR REPLACE để cập nhật nếu đã có, thêm mới nếu chưa có
            conn.execute("""
                INSERT INTO device_pricing (device_id, item_name, custom_price, custom_cost_price)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(device_id, item_name) DO UPDATE SET
                    custom_price = excluded.custom_price,
                    custom_cost_price = excluded.custom_cost_price
            """, (device_id, item_name, price, cost_price))
            conn.commit()
            
        logSystemEvent('custom_price_set', f'Set price for {item_name} on {device_id}')
        return jsonify({'success': True, 'message': 'Custom price set successfully'})

    except Exception as e:
        logger.error(f"Error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
@app.route('/api/products', methods=['GET'])
def getProducts():
    try:
        # 1. Lấy ID của máy đang gọi lên (Client phải gửi header này)
        device_id = request.headers.get('X-Device-ID')
        
        with getDatabaseConnection() as conn:
            conn.row_factory = sqlite3.Row # Để truy cập bằng tên cột
            
            # 2. Lấy danh sách sản phẩm gốc (Giá mặc định)
            base_products = {row['item_name']: dict(row) for row in conn.execute("SELECT * FROM inventory").fetchall()}
            
            # 3. Nếu có device_id, tìm xem có giá riêng không
            if device_id:
                overrides = conn.execute("""
                    SELECT item_name, custom_price, custom_cost_price 
                    FROM device_pricing 
                    WHERE device_id = ?
                """, (device_id,)).fetchall()
                
                # 4. Ghi đè giá riêng vào danh sách gốc
                for row in overrides:
                    item_name = row['item_name']
                    if item_name in base_products:
                        # Chỉ ghi đè nếu giá trị không phải None
                        if row['custom_price'] is not None:
                            base_products[item_name]['price'] = row['custom_price']
                        if row['custom_cost_price'] is not None:
                            base_products[item_name]['cost_price'] = row['custom_cost_price']
                            
                        # Đánh dấu để Client biết đây là giá riêng (Option)
                        base_products[item_name]['is_custom_price'] = True

            # Chuyển về dạng list để trả về JSON
            final_products_list = list(base_products.values())

        return jsonify({'success': True, 'products': final_products_list, 'for_device': device_id})
    except Exception as e:
        logger.error(f"Error in /api/products: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'Internal Server Error'}), 500

# =============================================================================
# ENDPOINT GHI NHẬN GIAO DỊCH
# =============================================================================

def calculate_points_earned(amount):
    """Hàm helper để tính điểm nhận được từ một giao dịch."""
    return int(amount / 1000)

@app.route('/api/transactions/record', methods=['POST'])
def recordTransaction():
    try:
        data = request.get_json()
        device_id = request.headers.get('X-Device-ID', 'UNKNOWN_DEVICE')
        logger.info(f"Received transaction data from {device_id}: {data}")

        required = ['total_amount', 'items']
        if not all(field in data for field in required):
            logger.warning(f"Bad request from {device_id}: Missing required fields.")
            return jsonify({'success': False, 'message': 'Missing required fields (total_amount, items)'}), 400

        total_amount = data['total_amount']
        items = data['items']
        customer_info = data.get('customer_info')
        
        with dbLock, getDatabaseConnection() as conn:
            cursor = conn.cursor()
            
            transaction_id = f"trans_{uuid.uuid4().hex[:10]}"
            items_str = json.dumps(items)
            now_iso = datetime.now(timezone.utc).isoformat()
            
            user_id = None
            
            # <<< THAY ĐỔI LỚN 1: Lấy user_id và new_total_points từ client >>>
            if customer_info and isinstance(customer_info, dict):
                user_id = customer_info.get('user_id')
                # Lấy trực tiếp số điểm cuối cùng mà client đã tính toán
                new_total_points = customer_info.get('new_total_points') 

            # 1. LƯU GIAO DỊCH (Không thay đổi)
            cursor.execute("""
                INSERT INTO transactions (transaction_id, total_amount, items, user_id, device_id, payment_status, created_at)
                VALUES (?, ?, ?, ?, ?, 'completed', ?)
            """, (transaction_id, total_amount, items_str, user_id, device_id, now_iso))
            logger.info(f"Transaction {transaction_id} inserted into database.")
            
            # 2. CẬP NHẬT KHO (MỚI THÊM)
            # Duyệt qua từng món hàng trong items để trừ kho
            for item in items:
                # item cần có key 'product_name' hoặc 'item_name' từ client gửi lên
                p_name = item.get('product_name') or item.get('name') 
                qty = item.get('quantity', 1)
                
                if p_name:
                    cursor.execute("""
                        UPDATE inventory 
                        SET units_left = units_left - ?, 
                            units_sold = units_sold + ? 
                        WHERE item_name = ?
                    """, (qty, qty, p_name))
            
            # 3. CẬP NHẬT ĐIỂM (LOGIC MỚI - SIÊU ĐƠN GIẢN)
            # Nếu client gửi lên user_id VÀ số điểm mới thì mới cập nhật
            if user_id and new_total_points is not None:
                logger.info(f"Processing points update for user '{user_id}' based on client data.")
                
                # <<< THAY ĐỔI LỚN 2: KHÔNG TÍNH TOÁN, CHỈ GHI ĐÈ >>>
                # Cập nhật thẳng số điểm mà client gửi lên.
                cursor.execute("UPDATE users SET points = ?, updated_at = ? WHERE user_id = ?", 
                               (new_total_points, now_iso, user_id))
                
                log_msg = (f"Points updated for user {user_id} via client instruction. "
                           f"New total points: {new_total_points}")
                logger.info(log_msg)
                logSystemEvent('points_updated_by_client', log_msg)
            else:
                logger.info(f"Transaction {transaction_id} is for a guest or has no points data. No points updated.")
        
        logSystemEvent('transaction_recorded', f'Transaction {transaction_id} from {device_id} recorded successfully.')
        return jsonify({
            'success': True, 
            'message': 'Transaction recorded and points updated successfully based on client data', 
            'transaction_id': transaction_id
        })

    except Exception as e:
        logger.error(f"CRITICAL ERROR in /api/transactions/record: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'Internal Server Error'}), 500

@app.route('/api/transactions', methods=['GET'])
def list_transactions():
    """
    Lấy danh sách lịch sử giao dịch.
    Hỗ trợ phân trang và lọc theo device_id hoặc user_id.
    - /api/transactions
    - /api/transactions?limit=10&offset=20
    - /api/transactions?device_id=VENDING_001
    - /api/transactions?user_id=user_xxxxxxxx
    """
    try:
        limit = int(request.args.get('limit', 20))
        offset = int(request.args.get('offset', 0))
        device_id = request.args.get('device_id')
        user_id = request.args.get('user_id')

        with dbLock, getDatabaseConnection() as conn:
            query = "SELECT * FROM transactions"
            count_query = "SELECT COUNT(*) as total FROM transactions"
            params = []
            conditions = []

            if device_id:
                conditions.append("device_id = ?")
                params.append(device_id)
            if user_id:
                conditions.append("user_id = ?")
                params.append(user_id)

            if conditions:
                where_clause = " WHERE " + " AND ".join(conditions)
                query += where_clause
                count_query += where_clause
            
            total_records = conn.execute(count_query, params).fetchone()['total']
            
            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            transactions = [dict(row) for row in conn.execute(query, params).fetchall()]

        return jsonify({
            'success': True,
            'total': total_records,
            'transactions': transactions
        })
    except Exception as e:
        logger.error(f"Error in /api/transactions: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'Internal Server Error'}), 500

@app.route('/api/inventory/stats', methods=['GET'])
def get_inventory_stats():
    try:
        with dbLock, getDatabaseConnection() as conn:
            # Lấy trực tiếp từ cột units_sold của bảng inventory
            # Cách này nhanh hơn nhiều so với việc parse lại JSON từ bảng transactions
            stats = conn.execute("SELECT item_name, units_sold FROM inventory ORDER BY units_sold DESC").fetchall()
            
            result = {row['item_name']: row['units_sold'] for row in stats}

        return jsonify({
            'success': True,
            'stats': result
        })
    except Exception as e:
        logger.error(f"Error in /api/inventory/stats: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'Internal Server Error'}), 500

# =============================================================================
# BỘ XỬ LÝ LỖI
# =============================================================================

@app.errorhandler(404)
def notFound(error):
    logger.warning(f"404 Not Found: {request.method} {request.path}")
    return jsonify({'success': False, 'message': 'Endpoint not found', 'path': request.path}), 404

# --- KHỞI CHẠY SERVER ---
if __name__ == '__main__':
    create_tables()
    populate_initial_products()
    
    print("*" * 60)
    print("  Vending Machine Central Server (Streamlined Version)")
    print("  Server is ready and listening...")
    print("*" * 60)
    
    # Chạy server ở cổng 5000 để khớp với client
    app.run(host='0.0.0.0', port=5000, debug=True)