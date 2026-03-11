# --- Vending Machine Central Server (PostgreSQL Version) ---

from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timezone
import json
import os
import psycopg2
import uuid
import logging
import unicodedata

# --- CẤU HÌNH ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://vending:vending123@localhost:5432/vending_machine')

app = Flask(__name__)
CORS(app)

# --- CÁC HÀM TIỆN ÍCH DATABASE ---
def getDatabaseConnection():
    """Thiết lập kết nối đến CSDL PostgreSQL."""
    return psycopg2.connect(DATABASE_URL)

def dict_fetchone(cursor):
    """Trả về một hàng dưới dạng dict."""
    row = cursor.fetchone()
    if row is None:
        return None
    columns = [desc[0] for desc in cursor.description]
    return dict(zip(columns, row))

def dict_fetchall(cursor):
    """Trả về tất cả hàng dưới dạng list of dict."""
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]

def create_tables():
    """Tạo các bảng CSDL cần thiết."""
    conn = getDatabaseConnection()
    try:
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

        # 2. Bảng inventory (MASTER DATA)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                id SERIAL PRIMARY KEY,
                item_name TEXT UNIQUE NOT NULL,
                price REAL NOT NULL,
                units_sold INTEGER DEFAULT 0,
                cost_price REAL DEFAULT 0,
                description TEXT
            )
        """)

        # 3. Bảng device_inventory (KHO RIÊNG TỪNG MÁY)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS device_inventory (
                id SERIAL PRIMARY KEY,
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
                id SERIAL PRIMARY KEY,
                device_id TEXT NOT NULL,
                item_name TEXT NOT NULL,
                custom_price REAL,
                custom_cost_price REAL,
                UNIQUE(device_id, item_name)
            )
        """)

        conn.commit()
        logger.info("Database tables checked/created.")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error creating tables: {e}")
        raise
    finally:
        conn.close()

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

        conn = getDatabaseConnection()
        try:
            cursor = conn.cursor()
            base_query = "SELECT user_id, full_name, phone_number, points, birthday, status, created_at FROM users"
            count_query = "SELECT COUNT(*) AS total FROM users"
            params = []

            if search:
                where_clause = " WHERE (full_name LIKE %s OR phone_number LIKE %s)"
                base_query += where_clause
                count_query += where_clause
                params.extend([f"%{search}%", f"%{search}%"])

            cursor.execute(count_query, params)
            total_records = cursor.fetchone()[0]

            base_query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
            params.extend([limit, offset])

            cursor.execute(base_query, params)
            users = dict_fetchall(cursor)
        finally:
            conn.close()

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

        conn = getDatabaseConnection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM users WHERE phone_number = %s", (data['phone_number'],))
            if cursor.fetchone():
                return jsonify({'success': False, 'message': 'Phone exists'}), 409
            cursor.execute("SELECT 1 FROM users WHERE user_id = %s", (user_id,))
            if cursor.fetchone():
                return jsonify({'success': False, 'message': 'ID exists'}), 409

            cursor.execute("""
                INSERT INTO users (user_id, full_name, phone_number, birthday, password, status, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, 'active', %s, %s)
            """, (user_id, data['full_name'], data['phone_number'], data['birthday'], data['password'], now_iso, now_iso))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

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
        conn = getDatabaseConnection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE phone_number = %s", (phone,))
            user = dict_fetchone(cursor)
            if user and user['password'] == password:
                return jsonify({'success': True, 'user': user})
        finally:
            conn.close()
    except Exception:
        pass
    return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

@app.route('/api/user/<string:user_id>', methods=['GET'])
def get_user_by_id(user_id):
    try:
        conn = getDatabaseConnection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, full_name, phone_number, points FROM users WHERE user_id = %s", (user_id,))
            user = dict_fetchone(cursor)
            if user:
                return jsonify({'success': True, 'user': user})
            return jsonify({'success': False}), 404
        finally:
            conn.close()
    except Exception:
        return jsonify({'success': False}), 500

# =============================================================================
# 2. API SẢN PHẨM & KHO
# =============================================================================
@app.route('/api/products/batch_sync', methods=['POST'])
def batchSyncProducts():
    """
    ❌ DEPRECATED - Client KHÔNG ĐƯỢC đẩy master data lên.
    Chỉ Admin Dashboard mới được tạo/sửa sản phẩm.
    """
    return jsonify({
        'success': False, 
        'message': 'API deprecated. Use Admin Dashboard to manage products.'
    }), 403

'''@app.route('/api/products/batch_sync', methods=['POST'])
def batchSyncProducts():
    """
    Đồng bộ sản phẩm:
    - inventory: CHỈ lưu tên, giá, ảnh.
    - device_inventory: Lưu tồn kho của máy.
    """
    try:
        data = request.get_json()
        device_id = request.headers.get('X-Device-ID') or data.get('products', [{}])[0].get('device_id')
        products = data.get('products', [])

        if not device_id:
            return jsonify({'success': False, 'message': 'Missing Device ID'}), 400

        now_iso = datetime.now(timezone.utc).isoformat()

        conn = getDatabaseConnection()
        try:
            cursor = conn.cursor()
            count = 0

            for p in products:
                name = p.get('name')
                price = p.get('price')
                image = p.get('image', '')
                qty = p.get('quantity', 0)

                # 1. Update MASTER DATA (inventory)
                cursor.execute("""
                    INSERT INTO inventory (item_name, price, cost_price, description)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT(item_name) DO UPDATE SET
                        description = EXCLUDED.description
                """, (name, price, price * 0.7, f"Image: {image}"))

                # 2. Update DEVICE INVENTORY (Kho riêng)
                cursor.execute("""
                    INSERT INTO device_inventory (device_id, item_name, units_left, last_updated)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT(device_id, item_name) DO UPDATE SET
                        units_left = EXCLUDED.units_left,
                        last_updated = EXCLUDED.last_updated
                """, (device_id, name, qty, now_iso))
                count += 1

            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

        logSystemEvent('batch_sync', f'Synced {count} items for {device_id}')
        return jsonify({'success': True, 'message': f'Synced {count} items'})
    except Exception as e:
        logger.error(f"Sync Error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500 '''

@app.route('/api/admin/create_product', methods=['POST'])
def admin_create_product():
    """
    Admin Dashboard: Tạo sản phẩm mới.
    Chỉ Admin mới có quyền gọi API này.
    """
    try:
        data = request.get_json()
        item_name = data.get('item_name')
        price = data.get('price', 0)
        cost_price = data.get('cost_price', 0)
        description = data.get('description', '')
        
        if not item_name:
            return jsonify({'success': False, 'message': 'Thiếu tên sản phẩm'}), 400

        conn = getDatabaseConnection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO inventory (item_name, price, cost_price, description)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT(item_name) DO NOTHING
            """, (item_name, price, cost_price, description))
            conn.commit()
        finally:
            conn.close()

        return jsonify({'success': True, 'message': f'Đã tạo sản phẩm: {item_name}'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/admin/add_stock', methods=['POST'])
def admin_add_stock():
    """
    Admin Dashboard: Nhập hàng vào kho cho một máy cụ thể.
    Đây là cách DUY NHẤT để tăng tồn kho.
    """
    try:
        data = request.get_json()
        device_id = data.get('device_id')
        item_name = data.get('item_name')
        quantity = data.get('quantity', 0)

        if not device_id or not item_name or quantity <= 0:
            return jsonify({'success': False, 'message': 'Thiếu thông tin'}), 400

        now_iso = datetime.now(timezone.utc).isoformat()
        conn = getDatabaseConnection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO device_inventory (device_id, item_name, units_left, last_updated)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT(device_id, item_name) DO UPDATE SET
                    units_left = device_inventory.units_left + %s,
                    last_updated = %s
            """, (device_id, item_name, quantity, now_iso, quantity, now_iso))
            conn.commit()
            
            # Log sự kiện nhập hàng
            logSystemEvent('stock_added', 
                f'Added {quantity} units of {item_name} to {device_id}')
        finally:
            conn.close()

        return jsonify({'success': True, 'message': f'Đã nhập {quantity} {item_name} cho {device_id}'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/products/set_custom', methods=['POST'])
def setDevicePrice():
    """Admin: Set giá riêng cho máy"""
    try:
        data = request.get_json()
        device_id = data.get('device_id')
        item_name = data.get('item_name')
        price = data.get('price')

        conn = getDatabaseConnection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO device_pricing (device_id, item_name, custom_price)
                VALUES (%s, %s, %s)
                ON CONFLICT(device_id, item_name) DO UPDATE SET custom_price = EXCLUDED.custom_price
            """, (device_id, item_name, price))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

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

        conn = getDatabaseConnection()
        try:
            cursor = conn.cursor()
            if device_id:
                # JOIN lấy tồn kho riêng của máy
                query = """
                    SELECT i.item_name, i.price, i.description,
                           COALESCE(d.units_left, 0) as units_left,
                           dp.custom_price
                    FROM inventory i
                    LEFT JOIN device_inventory d ON i.item_name = d.item_name AND d.device_id = %s
                    LEFT JOIN device_pricing dp ON i.item_name = dp.item_name AND dp.device_id = %s
                """
                cursor.execute(query, (device_id, device_id))
            else:
                # Admin/Mặc định: Lấy master data.
                cursor.execute("SELECT * FROM inventory")

            rows = dict_fetchall(cursor)
        finally:
            conn.close()

        final_list = []
        for p in rows:
            if device_id:
                # Nếu có giá riêng thì lấy, không thì giữ giá gốc
                if p.get('custom_price') is not None:
                    p['price'] = p['custom_price']
                # Nếu units_left bị None (do chưa sync kho), gán bằng 0
                if p.get('units_left') is None:
                    p['units_left'] = 0
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
        device_id = data.get('device_id') or request.headers.get('X-Device-ID') or 'UNKNOWN'

        total_amount = data['total_amount']
        items = data['items']
        customer_info = data.get('customer_info')

        conn = getDatabaseConnection()
        try:
            cursor = conn.cursor()

            # ─── 1. Lưu transaction ───
            transaction_id = f"trans_{uuid.uuid4().hex[:10]}"
            items_str = json.dumps(items)
            now_iso = datetime.now(timezone.utc).isoformat()
            user_id = customer_info.get('user_id') if customer_info else None

            cursor.execute("""
                INSERT INTO transactions 
                (transaction_id, total_amount, items, user_id, device_id, payment_status, created_at)
                VALUES (%s, %s, %s, %s, %s, 'completed', %s)
            """, (transaction_id, total_amount, items_str, user_id, device_id, now_iso))

            # ─── 2. Xử lý kho ───
            for item in items:
                p_name = item.get('product_name') or item.get('name') or item.get('item_name')
                qty = item.get('quantity', 1)

                if p_name:
                    # Trừ kho riêng của máy
                    cursor.execute("""
                        UPDATE device_inventory
                        SET units_left = units_left - %s
                        WHERE item_name = %s AND device_id = %s
                    """, (qty, p_name, device_id))

                    # Cộng tổng số đã bán (thống kê)
                    cursor.execute("""
                        UPDATE inventory
                        SET units_sold = units_sold + %s
                        WHERE item_name = %s
                    """, (qty, p_name))

            # ─── 3. Cập nhật điểm: SERVER TỰ TÍNH ───
            current_user_points = 0  # ✅ Khởi tạo mặc định

            if user_id:
                # Server tự tính điểm dựa trên số tiền
                points_earned = int(total_amount / 1000)

                # Cộng điểm và cập nhật thời gian
                cursor.execute("""
                    UPDATE users 
                    SET points = points + %s, updated_at = %s
                    WHERE user_id = %s
                """, (points_earned, now_iso, user_id))

                # Đọc lại điểm mới nhất để trả về cho Client
                cursor.execute(
                    "SELECT points FROM users WHERE user_id = %s", 
                    (user_id,)
                )
                row = cursor.fetchone()
                if row:
                    current_user_points = row[0]

            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

        logSystemEvent('transaction', f'Recorded {transaction_id} from {device_id}')

        return jsonify({
            'success': True,
            'transaction_id': transaction_id,
            'new_points': current_user_points
        })

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

        conn = getDatabaseConnection()
        try:
            cursor = conn.cursor()
            query = "SELECT * FROM transactions"
            count_query = "SELECT COUNT(*) FROM transactions"
            conditions = []
            params = []

            if device_id:
                conditions.append("device_id = %s")
                params.append(device_id)
            if user_id:
                conditions.append("user_id = %s")
                params.append(user_id)

            if conditions:
                clause = " WHERE " + " AND ".join(conditions)
                query += clause
                count_query += clause

            cursor.execute(count_query, params)
            total = cursor.fetchone()[0]

            query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
            params.extend([limit, offset])

            cursor.execute(query, params)
            trans = dict_fetchall(cursor)
        finally:
            conn.close()

        return jsonify({'success': True, 'total': total, 'transactions': trans})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/inventory/stats', methods=['GET'])
def get_inventory_stats():
    """Admin: Xem thống kê bán chạy"""
    try:
        conn = getDatabaseConnection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT item_name, units_sold FROM inventory ORDER BY units_sold DESC")
            rows = dict_fetchall(cursor)
            result = {row['item_name']: row['units_sold'] for row in rows}
        finally:
            conn.close()

        return jsonify({'success': True, 'stats': result})
    except Exception as e:
        return jsonify({'success': False}), 500

# =============================================================================
# 4. API CẬP NHẬT TÊN SP, GIÁ, SỐ LƯỢNG THEO YÊU CẦU
# =============================================================================

@app.route('/api/admin/update_product', methods=['POST'])
def admin_update_product():
    """
    API dành cho Dashboard Streamlit cập nhật thông tin sản phẩm.
    Hỗ trợ: Đổi tên, Đổi giá, Cập nhật tồn kho (Device).
    """
    try:
        data = request.get_json()
        old_name = data.get('old_name')
        new_name = data.get('new_name')
        new_price = data.get('price')
        add_stock = data.get('add_stock', 0)
        device_id = data.get('device_id')

        conn = getDatabaseConnection()
        try:
            cursor = conn.cursor()

            # 1. Xử lý ĐỔI TÊN
            if old_name and new_name and old_name != new_name:
                cursor.execute("SELECT 1 FROM inventory WHERE item_name = %s", (new_name,))
                if cursor.fetchone():
                    return jsonify({'success': False, 'message': 'Tên sản phẩm mới đã tồn tại!'}), 400

                cursor.execute("UPDATE inventory SET item_name = %s WHERE item_name = %s", (new_name, old_name))
                cursor.execute("UPDATE device_inventory SET item_name = %s WHERE item_name = %s", (new_name, old_name))
                cursor.execute("UPDATE device_pricing SET item_name = %s WHERE item_name = %s", (new_name, old_name))
                target_name = new_name
            else:
                target_name = old_name

            # 2. Xử lý ĐỔI GIÁ (Master Data)
            if new_price is not None:
                cursor.execute("UPDATE inventory SET price = %s WHERE item_name = %s", (new_price, target_name))

            # 3. Xử lý CẬP NHẬT KHO (Device Inventory)
            if device_id and add_stock != 0:
                cursor.execute("SELECT units_left FROM device_inventory WHERE device_id = %s AND item_name = %s", (device_id, target_name))
                row = cursor.fetchone()

                now_iso = datetime.now(timezone.utc).isoformat()
                if row:
                    cursor.execute("""
                        UPDATE device_inventory
                        SET units_left = units_left + %s, last_updated = %s
                        WHERE device_id = %s AND item_name = %s
                    """, (add_stock, now_iso, device_id, target_name))
                else:
                    cursor.execute("""
                        INSERT INTO device_inventory (device_id, item_name, units_left, last_updated)
                        VALUES (%s, %s, %s, %s)
                    """, (device_id, target_name, add_stock, now_iso))

            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

        return jsonify({'success': True, 'message': 'Cập nhật sản phẩm thành công'})
    except Exception as e:
        logger.error(f"Admin Update Error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/user/sync_profile', methods=['POST'])
def sync_user_profile():
    """
    API nhận thông tin user từ Client gửi lên để đồng bộ.
    CHỈ cập nhật thông tin cá nhân, KHÔNG ghi đè điểm.
    """
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'Missing user_id'}), 400

        full_name = data.get('full_name')
        phone = data.get('phone_number')
        dob = data.get('birthday')
        pwd = data.get('password', '123456')
        created_at = data.get('created_at', datetime.now(timezone.utc).isoformat())
        now_iso = datetime.now(timezone.utc).isoformat()

        conn = getDatabaseConnection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (user_id, full_name, phone_number, birthday, password, points, status, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, 0, 'active', %s, %s)
                ON CONFLICT(user_id) DO UPDATE SET
                    full_name = EXCLUDED.full_name,
                    phone_number = EXCLUDED.phone_number,
                    birthday = EXCLUDED.birthday,
                    password = EXCLUDED.password,
                    updated_at = EXCLUDED.updated_at
            """, (user_id, full_name, phone, dob, pwd, created_at, now_iso))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

        return jsonify({'success': True})

    except Exception as e:
        logger.error(f"Sync User Profile Error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

create_tables()

# --- KHỞI CHẠY ---
if __name__ == '__main__':
    print("Server Vending Machine running on port 5000...")
    app.run(host='0.0.0.0', port=5000, debug=False)
