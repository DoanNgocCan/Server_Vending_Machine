from flask import Blueprint, request, jsonify
from datetime import datetime, timezone
import logging

from database import getDatabaseConnection, dict_fetchall, dict_fetchone
from utils import logSystemEvent

logger = logging.getLogger(__name__)

device_bp = Blueprint('devices', __name__)


@device_bp.route('/api/devices', methods=['GET'])
def get_devices():
    """Admin: Lấy danh sách thiết bị từ bảng devices."""
    try:
        conn = getDatabaseConnection()
        try:
            cursor = conn.cursor()
            # Dùng LEFT JOIN để máy chưa có hàng vẫn hiện lên UI
            cursor.execute("""
                SELECT d.device_id,
                       COUNT(DISTINCT di.item_name) AS product_count,
                       COALESCE(SUM(di.units_left), 0) AS total_units,
                       MAX(d.last_active) AS last_sync
                FROM devices d
                LEFT JOIN device_inventory di ON d.device_id = di.device_id
                GROUP BY d.device_id
                ORDER BY d.device_id
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
                       di.slot_number,
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
    """Admin: Đặt tồn kho chính xác và gán số ô cho một sản phẩm trong máy."""
    try:
        data = request.get_json()
        units_left = data.get('units_left')
        slot_number = data.get('slot_number') # <-- LẤY SỐ Ô TỪ BODY

        if units_left is None or slot_number is None:
            return jsonify({'success': False, 'message': 'units_left và slot_number là bắt buộc'}), 400
        
        try:
            units_left = int(units_left)
            slot_number = int(slot_number)
        except (ValueError, TypeError):
            return jsonify({'success': False, 'message': 'Dữ liệu phải là số nguyên'}), 400

        now_iso = datetime.now(timezone.utc).isoformat()
        conn = getDatabaseConnection()
        try:
            cursor = conn.cursor()
            
            # 1. Kiểm tra xem ô (slot_number) này đã bị sản phẩm KHÁC chiếm chưa
            cursor.execute("SELECT item_name FROM device_inventory WHERE device_id = %s AND slot_number = %s", (device_id, slot_number))
            row = cursor.fetchone()
            if row and row['item_name'] != item_name:
                # Gỡ sản phẩm cũ khỏi ô này
                cursor.execute("DELETE FROM device_inventory WHERE device_id = %s AND slot_number = %s", (device_id, slot_number))
            
            # 2. Kiểm tra xem sản phẩm này đã có trong máy chưa
            cursor.execute("SELECT 1 FROM device_inventory WHERE device_id = %s AND item_name = %s", (device_id, item_name))
            if cursor.fetchone():
                # Cập nhật số lượng và số ô mới
                cursor.execute("""
                    UPDATE device_inventory 
                    SET units_left = %s, slot_number = %s, last_updated = %s
                    WHERE device_id = %s AND item_name = %s
                """, (units_left, slot_number, now_iso, device_id, item_name))
            else:
                # Thêm mới vào máy
                cursor.execute("""
                    INSERT INTO device_inventory (device_id, item_name, units_left, slot_number, last_updated)
                    VALUES (%s, %s, %s, %s, %s)
                """, (device_id, item_name, units_left, slot_number, now_iso))
                
            conn.commit()
            logSystemEvent('inventory_update', f'{device_id}: {item_name} set to {units_left}')

            # ======== THÊM MỚI TỪ ĐÂY ĐỂ ĐỒNG BỘ CLIENT ========
            try:
                cursor.execute("""
                    SELECT i.price, dp.custom_price 
                    FROM inventory i
                    LEFT JOIN device_pricing dp ON dp.item_name = i.item_name AND dp.device_id = %s
                    WHERE i.item_name = %s
                """, (device_id, item_name))
                row = cursor.fetchone()
                # Lấy giá riêng của máy (nếu có), không thì lấy giá gốc
                final_price = row[1] if row and row[1] is not None else (row[0] if row else 0)
                
                from mqtt_publisher import get_publisher
                get_publisher().publish_product_update(item_name, final_price, int(units_left))
            except Exception as mqtt_err:
                logger.warning(f"MQTT publish failed in PUT inventory: {mqtt_err}")
            # ====================================================

        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

        return jsonify({'success': True, 'message': f'Đã cập nhật tồn kho {item_name} = {units_left}'})
    except Exception as e:
        logger.error(f"Update Device Inventory Error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
@device_bp.route('/api/devices/<string:device_id>/inventory/<string:item_name>', methods=['DELETE'])
def remove_device_inventory(device_id, item_name):
    """Admin: Gỡ hoàn toàn một sản phẩm khỏi một máy cụ thể."""
    try:
        conn = getDatabaseConnection()
        try:
            cursor = conn.cursor()
            
            # 1. Xóa khỏi bảng tồn kho của máy này
            cursor.execute("""
                DELETE FROM device_inventory 
                WHERE device_id = %s AND item_name = %s
            """, (device_id, item_name))
            
            # 2. Xóa luôn giá cấu hình riêng của máy này (nếu có)
            cursor.execute("""
                DELETE FROM device_pricing 
                WHERE device_id = %s AND item_name = %s
            """, (device_id, item_name))
            
            conn.commit()
            logSystemEvent('inventory_removed', f'Removed {item_name} from {device_id}')
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

        # (Tùy chọn) Bắn MQTT update để máy trạm cập nhật lại UI ngay lập tức
        try:
            from mqtt_publisher import get_publisher
            get_publisher().publish_product_update(item_name, 0, 0)
        except Exception as mqtt_err:
            logger.warning(f"MQTT publish failed: {mqtt_err}")

        return jsonify({'success': True, 'message': f'Đã gỡ {item_name} khỏi {device_id}'})
    except Exception as e:
        logger.error(f"Remove Device Inventory Error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500