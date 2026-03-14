from flask import Blueprint, request, jsonify
from datetime import datetime, timezone
import json
import uuid
import logging

from database import getDatabaseConnection, dict_fetchall
from utils import logSystemEvent

logger = logging.getLogger(__name__)

trans_bp = Blueprint('transactions', __name__)

@trans_bp.route('/api/transactions/record', methods=['POST'])
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

            # 1. Lưu transaction
            transaction_id = f"trans_{uuid.uuid4().hex[:10]}"
            items_str = json.dumps(items)
            now_iso = datetime.now(timezone.utc).isoformat()
            user_id = customer_info.get('user_id') if customer_info else None

            cursor.execute("""
                INSERT INTO transactions 
                (transaction_id, total_amount, items, user_id, device_id, payment_status, created_at)
                VALUES (%s, %s, %s, %s, %s, 'completed', %s)
            """, (transaction_id, total_amount, items_str, user_id, device_id, now_iso))

            # 2. Xử lý kho
            for item in items:
                p_name = item.get('product_name') or item.get('name') or item.get('item_name')
                qty = item.get('quantity', 1)

                if p_name:
                    cursor.execute("""
                        UPDATE device_inventory
                        SET units_left = units_left - %s
                        WHERE item_name = %s AND device_id = %s
                    """, (qty, p_name, device_id))

                    cursor.execute("""
                        UPDATE inventory
                        SET units_sold = units_sold + %s
                        WHERE item_name = %s
                    """, (qty, p_name))

            # 3. Cập nhật điểm
            current_user_points = 0 

            if user_id:
                points_earned = int(total_amount / 1000)
                cursor.execute("""
                    UPDATE users 
                    SET points = points + %s, updated_at = %s
                    WHERE user_id = %s
                """, (points_earned, now_iso, user_id))

                cursor.execute("SELECT points FROM users WHERE user_id = %s", (user_id,))
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

@trans_bp.route('/api/transactions', methods=['GET'])
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

@trans_bp.route('/api/inventory/stats', methods=['GET'])
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