from flask import Blueprint, request, jsonify, send_from_directory
from datetime import datetime, timezone
import logging
import os
import uuid

from database import getDatabaseConnection, dict_fetchall
from utils import logSystemEvent

IMAGES_DIR = os.environ.get('IMAGES_DIR', '/app/images')
os.makedirs(IMAGES_DIR, exist_ok=True)

logger = logging.getLogger(__name__)

product_bp = Blueprint('products', __name__)

@product_bp.route('/api/products/batch_sync', methods=['POST'])
def batchSyncProducts():
    """
    ❌ DEPRECATED - Client KHÔNG ĐƯỢC đẩy master data lên.
    Chỉ Admin Dashboard mới được tạo/sửa sản phẩm.
    """
    return jsonify({
        'success': False, 
        'message': 'API deprecated. Use Admin Dashboard to manage products.'
    }), 403

@product_bp.route('/api/admin/create_product', methods=['POST'])
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

@product_bp.route('/api/admin/add_stock', methods=['POST'])
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
            
            logSystemEvent('stock_added', f'Added {quantity} units of {item_name} to {device_id}')
        finally:
            conn.close()

        return jsonify({'success': True, 'message': f'Đã nhập {quantity} {item_name} cho {device_id}'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@product_bp.route('/api/products/set_custom', methods=['POST'])
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

@product_bp.route('/api/products', methods=['GET'])
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
                cursor.execute("SELECT * FROM inventory")

            rows = dict_fetchall(cursor)
        finally:
            conn.close()

        final_list = []
        for p in rows:
            if device_id:
                if p.get('custom_price') is not None:
                    p['price'] = p['custom_price']
                if p.get('units_left') is None:
                    p['units_left'] = 0
            p.pop('custom_price', None)
            final_list.append(p)

        return jsonify({'success': True, 'products': final_list})
    except Exception as e:
        logger.error(f"Get Products Error: {e}")
        return jsonify({'success': False}), 500

@product_bp.route('/api/admin/update_product', methods=['POST'])
def admin_update_product():
    """
    API dành cho Dashboard Streamlit cập nhật thông tin sản phẩm.
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


@product_bp.route('/api/admin/products/<string:item_name>', methods=['DELETE'])
def admin_delete_product(item_name):
    """Admin: Xóa sản phẩm khỏi master data và tất cả kho máy."""
    try:
        conn = getDatabaseConnection()
        try:
            cursor = conn.cursor()
            # Lấy image_url trước khi xóa để có thể xóa file ảnh
            cursor.execute("SELECT image_url FROM inventory WHERE item_name = %s", (item_name,))
            row = cursor.fetchone()
            if not row:
                return jsonify({'success': False, 'message': 'Sản phẩm không tồn tại'}), 404

            image_url = row[0]

            cursor.execute("DELETE FROM device_pricing WHERE item_name = %s", (item_name,))
            cursor.execute("DELETE FROM device_inventory WHERE item_name = %s", (item_name,))
            cursor.execute("DELETE FROM inventory WHERE item_name = %s", (item_name,))
            conn.commit()
            logSystemEvent('product_deleted', f'Deleted product: {item_name}')
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

        # Xóa file ảnh nếu có
        if image_url:
            filename = os.path.basename(image_url)
            filepath = os.path.join(IMAGES_DIR, filename)
            if os.path.exists(filepath):
                os.remove(filepath)

        return jsonify({'success': True, 'message': f'Đã xóa sản phẩm: {item_name}'})
    except Exception as e:
        logger.error(f"Admin Delete Product Error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}


def _allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@product_bp.route('/api/admin/upload_image', methods=['POST'])
def admin_upload_image():
    """Admin: Upload ảnh cho sản phẩm."""
    try:
        item_name = request.form.get('item_name')
        if not item_name:
            return jsonify({'success': False, 'message': 'Thiếu item_name'}), 400

        if 'image' not in request.files:
            return jsonify({'success': False, 'message': 'Thiếu file ảnh'}), 400

        file = request.files['image']
        if file.filename == '':
            return jsonify({'success': False, 'message': 'Chưa chọn file'}), 400

        if not _allowed_file(file.filename):
            return jsonify({'success': False, 'message': 'Định dạng không hỗ trợ (jpg, jpeg, png, webp)'}), 400

        ext = file.filename.rsplit('.', 1)[1].lower()
        unique_name = f"{uuid.uuid4().hex}.{ext}"
        save_path = os.path.join(IMAGES_DIR, unique_name)
        file.save(save_path)

        image_url = f"/api/images/{unique_name}"

        conn = getDatabaseConnection()
        try:
            cursor = conn.cursor()
            # Xóa ảnh cũ nếu có
            cursor.execute("SELECT image_url FROM inventory WHERE item_name = %s", (item_name,))
            existing = cursor.fetchone()
            if existing and existing[0]:
                old_filename = os.path.basename(existing[0])
                old_path = os.path.join(IMAGES_DIR, old_filename)
                if os.path.exists(old_path):
                    os.remove(old_path)

            cursor.execute("UPDATE inventory SET image_url = %s WHERE item_name = %s", (image_url, item_name))
            conn.commit()
        except Exception:
            conn.rollback()
            if os.path.exists(save_path):
                os.remove(save_path)
            raise
        finally:
            conn.close()

        logSystemEvent('image_uploaded', f'Image uploaded for {item_name}: {unique_name}')
        return jsonify({'success': True, 'image_url': image_url, 'filename': unique_name})
    except Exception as e:
        logger.error(f"Upload Image Error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@product_bp.route('/api/images/<path:filename>', methods=['GET'])
def serve_image(filename):
    """Serve ảnh sản phẩm."""
    return send_from_directory(IMAGES_DIR, filename)