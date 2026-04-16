from flask import Blueprint, request, jsonify
from datetime import datetime, timezone
import logging

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
            base_query = "SELECT user_id, full_name, phone_number, points, email, status, created_at FROM users"
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
            if user and user['password'] == password:
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
            cursor.execute("SELECT user_id, full_name, phone_number, points FROM users WHERE user_id = %s", (user_id,))
            user = dict_fetchone(cursor)
            if user:
                return jsonify({'success': True, 'user': user})
            return jsonify({'success': False}), 404
        finally:
            conn.close()
    except Exception:
        return jsonify({'success': False}), 500

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