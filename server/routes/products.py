# --- Products & Inventory API Routes ---

import logging
from datetime import datetime, timezone

from flask import Blueprint, request, jsonify

from database import getDatabaseConnection, dict_fetchall
from utils import logSystemEvent

logger = logging.getLogger(__name__)

products_bp = Blueprint('products', __name__)


# =============================================================================
# 2. API SẢN PHẨM & KHO
# =============================================================================

@products_bp.route('/api/products/batch_sync', methods=['POST'])
def batchSyncProducts():
    """
    ❌ DEPRECATED - Client KHÔNG ĐƯỢC đẩy master data lên.
    Chỉ Admin Dashboard mới được tạo/sửa sản phẩm.
    """
    return jsonify({
        'success': False,
        'message': 'API deprecated. Use Admin Dashboard to manage products.'
    }), 403


@products_bp.route('/api/admin/create_product', methods=['POST'])
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


@products_bp.route('/api/admin/add_stock', methods=['POST'])
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


@products_bp.route('/api/products/set_custom', methods=['POST'])
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


@products_bp.route('/api/products', methods=['GET'])
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
# 4. API CẬP NHẬT TÊN SP, GIÁ, SỐ LƯỢNG THEO YÊU CẦU
# =============================================================================

@products_bp.route('/api/admin/update_product', methods=['POST'])
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
