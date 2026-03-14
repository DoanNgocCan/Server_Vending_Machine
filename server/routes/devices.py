from flask import Blueprint, request, jsonify
from datetime import datetime, timezone
import logging

from database import getDatabaseConnection, dict_fetchall, dict_fetchone
from utils import logSystemEvent

logger = logging.getLogger(__name__)

device_bp = Blueprint('devices', __name__)


@device_bp.route('/api/devices', methods=['GET'])
def get_devices():
    """Admin: Lấy danh sách thiết bị từ device_inventory."""
    try:
        conn = getDatabaseConnection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT device_id,
                       COUNT(DISTINCT item_name) AS product_count,
                       SUM(units_left) AS total_units,
                       MAX(last_updated) AS last_sync
                FROM device_inventory
                GROUP BY device_id
                ORDER BY device_id
            """)
            devices = dict_fetchall(cursor)
        finally:
            conn.close()

        return jsonify({'success': True, 'devices': devices})
    except Exception as e:
        logger.error(f"Get Devices Error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@device_bp.route('/api/devices/<string:device_id>/inventory', methods=['GET'])
def get_device_inventory(device_id):
    """Admin: Lấy toàn bộ tồn kho của một máy."""
    try:
        conn = getDatabaseConnection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT di.item_name,
                       di.units_left,
                       di.last_updated,
                       i.price,
                       i.description,
                       i.image_url,
                       dp.custom_price
                FROM device_inventory di
                JOIN inventory i ON di.item_name = i.item_name
                LEFT JOIN device_pricing dp ON di.item_name = dp.item_name AND dp.device_id = %s
                WHERE di.device_id = %s
                ORDER BY di.item_name
            """, (device_id, device_id))
            rows = dict_fetchall(cursor)
        finally:
            conn.close()

        return jsonify({'success': True, 'device_id': device_id, 'inventory': rows})
    except Exception as e:
        logger.error(f"Get Device Inventory Error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@device_bp.route('/api/devices/<string:device_id>/inventory/<string:item_name>', methods=['PUT'])
def update_device_inventory(device_id, item_name):
    """Admin: Đặt tồn kho chính xác (không cộng thêm) cho một sản phẩm trong máy."""
    try:
        data = request.get_json()
        units_left = data.get('units_left')

        if units_left is None:
            return jsonify({'success': False, 'message': 'units_left là bắt buộc'}), 400
        try:
            units_left = int(units_left)
        except (ValueError, TypeError):
            return jsonify({'success': False, 'message': 'units_left phải là số nguyên'}), 400
        if units_left < 0:
            return jsonify({'success': False, 'message': 'units_left phải >= 0'}), 400

        now_iso = datetime.now(timezone.utc).isoformat()
        conn = getDatabaseConnection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO device_inventory (device_id, item_name, units_left, last_updated)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT(device_id, item_name) DO UPDATE SET
                    units_left = EXCLUDED.units_left,
                    last_updated = EXCLUDED.last_updated
            """, (device_id, item_name, int(units_left), now_iso))
            conn.commit()
            logSystemEvent('inventory_update', f'{device_id}: {item_name} set to {units_left}')
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

        return jsonify({'success': True, 'message': f'Đã cập nhật tồn kho {item_name} = {units_left}'})
    except Exception as e:
        logger.error(f"Update Device Inventory Error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
