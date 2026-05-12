from flask import Blueprint, request, jsonify
from datetime import datetime, timezone
import logging
import json
from collections import Counter

# Import các hàm dùng chung từ database và utils
from database import getDatabaseConnection, dict_fetchone, dict_fetchall
from utils import logSystemEvent

logger = logging.getLogger(__name__)
user_bp = Blueprint('users', __name__)

@user_bp.route('/api/users', methods=['GET'])
def listUsers():
    try:
        limit = int(request.args.get('limit', 20))
        offset = int(request.args.get('offset', 0))
        search = request.args.get('search', None)

        conn = getDatabaseConnection()
        try:
            cursor = conn.cursor()
            base_query = "SELECT user_id, full_name, phone_number, points, email, status, created_at, password FROM users"
            count_query = "SELECT COUNT(*) AS total FROM users"
            params = []

            if search:
                where_clause = " WHERE (full_name LIKE %s OR phone_number LIKE %s OR email LIKE %s)"
                base_query += where_clause
                count_query += where_clause
                params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])

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

@user_bp.route('/api/user/register', methods=['POST'])
def registerUser():
    try:
        data = request.get_json()
        # Thay 'birthday' bằng 'email' và thêm 'confirm_password'
        required = ['user_id', 'full_name', 'phone_number', 'email', 'password', 'confirm_password']
        if not all(field in data for field in required):
            return jsonify({'success': False, 'message': 'Missing fields'}), 400

        # Kiểm tra xác nhận mật khẩu
        if data['password'] != data['confirm_password']:
            return jsonify({'success': False, 'message': 'Passwords do not match'}), 400
        user_id = data['user_id']
        now_iso = datetime.now(timezone.utc).isoformat()

        conn = getDatabaseConnection()
        try:
            cursor = conn.cursor()
            # Kiểm tra trùng SĐT hoặc Email
            cursor.execute("SELECT 1 FROM users WHERE phone_number = %s OR email = %s", (data['phone_number'], data['email']))
            if cursor.fetchone():
                return jsonify({'success': False, 'message': 'Phone or Email already exists'}), 409
            
            cursor.execute("SELECT 1 FROM users WHERE user_id = %s", (user_id,))
            if cursor.fetchone():
                return jsonify({'success': False, 'message': 'ID exists'}), 409

            cursor.execute("""
                INSERT INTO users (user_id, full_name, phone_number, email, password, status, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, 'active', %s, %s)
            """, (user_id, data['full_name'], data['phone_number'], data['email'], data['password'], now_iso, now_iso))
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

@user_bp.route('/api/user/login', methods=['POST'])
def loginUser():
    data = request.get_json()
    # Nhận chung 1 trường login_id (có thể là email hoặc sđt)
    login_id = data.get('login_id') 
    password = data.get('password')
    try:
        conn = getDatabaseConnection()
        try:
            cursor = conn.cursor()
            # Tìm kiếm theo SĐT hoặc Email
            cursor.execute("SELECT * FROM users WHERE phone_number = %s OR email = %s", (login_id, login_id))
            user = dict_fetchone(cursor)

            if user and user['password'] == str(password):
                return jsonify({'success': True, 'user': user})

        finally:
            conn.close()
    except Exception as e:
        logger.error(f"Login error: {e}")
    return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

@user_bp.route('/api/user/<string:user_id>', methods=['GET'])
def get_user_by_id(user_id):
    try:
        conn = getDatabaseConnection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, full_name, phone_number, email, points, password FROM users WHERE user_id = %s", (user_id,))
            user = dict_fetchone(cursor)
            if user:
                return jsonify({'success': True, 'user': user})
            return jsonify({'success': False}), 404
        finally:
            conn.close()
    except Exception:
        return jsonify({'success': False}), 500
@user_bp.route('/api/users/<string:user_id>/recommendation', methods=['GET'])
def get_user_recommendation(user_id):
    try:
        conn = getDatabaseConnection()
        try:
            cursor = conn.cursor()
            
            # BƯỚC 1: Lấy lịch sử mua hàng, sắp xếp từ MỚI NHẤT đến CŨ NHẤT (QUAN TRỌNG)
            cursor.execute("SELECT items FROM transactions WHERE user_id = %s ORDER BY created_at DESC", (user_id,))
            rows = cursor.fetchall()
            
            if not rows:
                return jsonify({"status": "empty", "message": "Chưa có lịch sử mua hàng"}), 200

            product_counts = Counter()
            recent_order_list = [] # Mảng lưu vết để giải quyết hòa điểm

            # BƯỚC 2: Thống kê số lượng và ghi nhận độ "tươi mới" của sản phẩm
            for row in rows:
                try:
                    items_list = json.loads(row[0])
                    for item in items_list:
                        p_name = item.get('product_name') or item.get('name') or item.get('item_name')
                        qty = item.get('quantity', 1)
                        if p_name:
                            # Cộng dồn số lượng mua
                            product_counts[p_name] += qty
                            
                            # Món nào gặp trước (từ đơn mới nhất) sẽ được chốt vị trí đầu trong danh sách này
                            if p_name not in recent_order_list:
                                recent_order_list.append(p_name)
                except Exception as parse_err:
                    logger.warning(f"Lỗi phân tích JSON: {parse_err}")
                    continue
            
            if not product_counts:
                return jsonify({"status": "empty", "message": "Không tìm thấy sản phẩm hợp lệ"}), 200

            # BƯỚC 3: XỬ LÝ HÒA ĐIỂM (TIE-BREAKER)
            # Tìm mức số lượng cao nhất (VD: Mua nhiều nhất là 1)
            max_qty = max(product_counts.values())
            
            # Lấy ra TẤT CẢ các món cùng đạt mốc max_qty này
            top_candidates = [p_name for p_name, count in product_counts.items() if count == max_qty]

            # Quét mảng recent_order_list từ trên xuống. Món nào trong nhóm đồng hạng xuất hiện đầu tiên -> Chọn luôn!
            top_product_name = next(p for p in recent_order_list if p in top_candidates)

            # BƯỚC 4: Lấy dữ liệu sản phẩm để gửi về giao diện (UI)
            query = """
                SELECT id, item_name AS name, price, image_url 
                FROM inventory 
                WHERE item_name = %s
            """
            cursor.execute(query, (top_product_name,))
            recommended_product = dict_fetchone(cursor)
            
        finally:
            conn.close()
            
        if recommended_product:
            return jsonify({"status": "success", "data": recommended_product}), 200
            
        return jsonify({"status": "empty", "message": "Sản phẩm không còn trong hệ thống"}), 200

    except Exception as e:
        logger.error(f"Error Recommendation API: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
@user_bp.route('/api/user/sync_profile', methods=['POST'])
def sync_user_profile():
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'Missing user_id'}), 400

        full_name = data.get('full_name')
        phone = data.get('phone_number')
        email = data.get('email')  # Đã đổi từ dob sang email
        pwd = data.get('password', '123456')
        created_at = data.get('created_at', datetime.now(timezone.utc).isoformat())
        now_iso = datetime.now(timezone.utc).isoformat()

        conn = getDatabaseConnection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (user_id, full_name, phone_number, email, password, points, status, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, 0, 'active', %s, %s)
                ON CONFLICT(user_id) DO UPDATE SET
                    full_name = EXCLUDED.full_name,
                    phone_number = EXCLUDED.phone_number,
                    email = EXCLUDED.email,    -- Sửa birthday thành email ở đây
                    password = EXCLUDED.password,
                    updated_at = EXCLUDED.updated_at
            """, (user_id, full_name, phone, email, pwd, created_at, now_iso))
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