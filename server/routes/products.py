from flask import Blueprint, request, jsonify, send_from_directory
from datetime import datetime, timezone
import logging
import os
import time

from database import getDatabaseConnection, dict_fetchall, dict_fetchone
from utils import logSystemEvent
from mqtt_publisher import get_publisher

logger = logging.getLogger(__name__)

product_bp = Blueprint('products', __name__)

# ---------------------------------------------------------------------------
# Image upload helpers
# ---------------------------------------------------------------------------
IMAGES_DIR          = os.path.join(os.path.dirname(__file__), '..', 'static', 'images')
ALLOWED_EXTENSIONS  = {'jpg', 'jpeg', 'png', 'webp'}
MAX_IMAGE_SIZE      = int(os.environ.get('MAX_IMAGE_SIZE', 5 * 1024 * 1024))  # 5 MB

_MIME_MAP = {
    'jpg':  'image/jpeg',
    'jpeg': 'image/jpeg',
    'png':  'image/png',
    'webp': 'image/webp',
}


def _allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def _secure_basename(filename: str) -> str:
    """Return the basename with only safe characters (no path traversal)."""
    name = os.path.basename(filename)
    # Keep only alphanumeric, dash, underscore, and dot
    safe = ''.join(c for c in name if c.isalnum() or c in ('-', '_', '.'))
    return safe or 'upload'


def _save_image(file_storage, product_id: str) -> tuple[str, str]:
    """
    Validate, save an uploaded image and return (filename, url).
    Raises ValueError on validation errors.
    """
    if not file_storage or file_storage.filename == '':
        raise ValueError('No image file provided')

    original = _secure_basename(file_storage.filename)
    if not _allowed_file(original):
        raise ValueError(f'Invalid file type. Allowed: {", ".join(ALLOWED_EXTENSIONS)}')

    ext = original.rsplit('.', 1)[1].lower()

    # Check size before reading fully
    try:
        file_storage.seek(0, 2)
        size = file_storage.tell()
        file_storage.seek(0)
    except (OSError, AttributeError):
        raise ValueError('Unable to process file stream')
    if size > MAX_IMAGE_SIZE:
        raise ValueError(f'File too large. Maximum size is {MAX_IMAGE_SIZE // 1024 // 1024} MB')

    # Generate unique filename: {product_id}_{timestamp}.{ext}
    timestamp   = int(time.time())
    safe_id     = _secure_basename(product_id)
    filename    = f'{safe_id}_{timestamp}.{ext}'
    dest_path   = os.path.join(IMAGES_DIR, filename)

    os.makedirs(IMAGES_DIR, exist_ok=True)
    file_storage.save(dest_path)

    image_url = f'/api/images/{filename}'
    return filename, image_url

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
    Accepts JSON *or* multipart/form-data (with optional image file).
    """
    try:
        # Support both JSON and multipart form
        if request.content_type and 'multipart/form-data' in request.content_type:
            item_name   = request.form.get('item_name', '')
            price       = float(request.form.get('price', 0))
            cost_price  = float(request.form.get('cost_price', 0))
            description = request.form.get('description', '')
            image_file  = request.files.get('image')
        else:
            data        = request.get_json() or {}
            item_name   = data.get('item_name', '')
            price       = data.get('price', 0)
            cost_price  = data.get('cost_price', 0)
            description = data.get('description', '')
            image_file  = None

        if not item_name:
            return jsonify({'success': False, 'message': 'Thiếu tên sản phẩm'}), 400

        image_filename = None
        image_url      = None
        if image_file:
            try:
                image_filename, image_url = _save_image(image_file, item_name)
            except ValueError as ve:
                return jsonify({'success': False, 'message': str(ve)}), 400

        conn = getDatabaseConnection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO inventory (item_name, price, cost_price, description, image_filename, image_url)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT(item_name) DO NOTHING
            """, (item_name, price, cost_price, description, image_filename, image_url))
            conn.commit()
        finally:
            conn.close()

        get_publisher().publish_new_product(item_name)

        return jsonify({'success': True, 'message': f'Đã tạo sản phẩm: {item_name}',
                        'image_url': image_url})
    except Exception as e:
        logger.error("Admin Create Product Error: %s", e)
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

        # Fetch updated units_left for this device to include in the MQTT payload
        try:
            conn2 = getDatabaseConnection()
            try:
                cursor2 = conn2.cursor()
                cursor2.execute("""
                    SELECT d.units_left, i.price
                    FROM device_inventory d
                    JOIN inventory i ON i.item_name = d.item_name
                    WHERE d.device_id = %s AND d.item_name = %s
                """, (device_id, item_name))
                row = cursor2.fetchone()
                units_left = row[0] if row else quantity
                price      = row[1] if row else 0
            finally:
                conn2.close()

            get_publisher().publish_product_update(item_name, price, units_left)
        except Exception as mqtt_err:
            logger.warning("MQTT publish after add_stock failed: %s", mqtt_err)

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
    Client: Lấy danh sách sản phẩm kèm image_url.
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
                           i.image_filename, i.image_url, i.created_at,
                           COALESCE(d.units_left, 0) as units_left,
                           dp.custom_price
                    FROM inventory i
                    LEFT JOIN device_inventory d ON i.item_name = d.item_name AND d.device_id = %s
                    LEFT JOIN device_pricing dp ON i.item_name = dp.item_name AND dp.device_id = %s
                """
                cursor.execute(query, (device_id, device_id))
            else:
                cursor.execute(
                    "SELECT id, item_name, price, cost_price, description, "
                    "image_filename, image_url, created_at, updated_at FROM inventory"
                )

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
            # Serialize timestamps
            for ts_field in ('created_at', 'updated_at'):
                if p.get(ts_field) and hasattr(p[ts_field], 'isoformat'):
                    p[ts_field] = p[ts_field].isoformat()
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

        get_publisher().publish_product_modified(target_name)

        return jsonify({'success': True, 'message': 'Cập nhật sản phẩm thành công'})
    except Exception as e:
        logger.error(f"Admin Update Error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


# ---------------------------------------------------------------------------
# GET /api/products/<product_id>  – single product detail
# ---------------------------------------------------------------------------

@product_bp.route('/api/products/<product_id>', methods=['GET'])
def get_single_product(product_id):
    """
    Return complete details for one product (by item_name or numeric id).
    Called by the client after receiving an MQTT data_changed notification.
    """
    try:
        device_id = request.headers.get('X-Device-ID')
        conn = getDatabaseConnection()
        try:
            cursor = conn.cursor()
            if device_id:
                query = """
                    SELECT i.id, i.item_name, i.price, i.description,
                           i.image_filename, i.image_url, i.created_at, i.updated_at,
                           COALESCE(d.units_left, 0) as units_left,
                           dp.custom_price
                    FROM inventory i
                    LEFT JOIN device_inventory d
                           ON i.item_name = d.item_name AND d.device_id = %s
                    LEFT JOIN device_pricing dp
                           ON i.item_name = dp.item_name AND dp.device_id = %s
                    WHERE i.item_name = %s OR i.id::TEXT = %s
                """
                cursor.execute(query, (device_id, device_id, product_id, product_id))
            else:
                cursor.execute(
                    "SELECT id, item_name, price, cost_price, description, "
                    "image_filename, image_url, created_at, updated_at "
                    "FROM inventory WHERE item_name = %s OR id::TEXT = %s",
                    (product_id, product_id),
                )
            product = dict_fetchone(cursor)
        finally:
            conn.close()

        if not product:
            return jsonify({'success': False, 'message': 'Product not found'}), 404

        if device_id:
            if product.get('custom_price') is not None:
                product['price'] = product['custom_price']
        product.pop('custom_price', None)
        for ts_field in ('created_at', 'updated_at'):
            if product.get(ts_field) and hasattr(product[ts_field], 'isoformat'):
                product[ts_field] = product[ts_field].isoformat()

        return jsonify({'success': True, 'product': product})
    except Exception as e:
        logger.error("Get Single Product Error: %s", e)
        return jsonify({'success': False, 'message': str(e)}), 500


# ---------------------------------------------------------------------------
# GET /api/images/<filename>  – serve product images
# ---------------------------------------------------------------------------

@product_bp.route('/api/images/<filename>', methods=['GET'])
def serve_image(filename):
    """
    Serve a product image from server/static/images/.
    Returns 404 if the file does not exist.
    """
    safe_name = _secure_basename(filename)
    if not safe_name or not _allowed_file(safe_name):
        return jsonify({'success': False, 'message': 'Invalid filename'}), 400

    abs_images_dir = os.path.abspath(IMAGES_DIR)
    file_path = os.path.join(abs_images_dir, safe_name)

    if not os.path.isfile(file_path):
        return jsonify({'success': False, 'message': 'Image not found'}), 404

    ext  = safe_name.rsplit('.', 1)[1].lower()
    mime = _MIME_MAP.get(ext, 'application/octet-stream')
    return send_from_directory(abs_images_dir, safe_name, mimetype=mime)


# ---------------------------------------------------------------------------
# POST /api/admin/upload_image  – upload / replace image for a product
# ---------------------------------------------------------------------------

@product_bp.route('/api/admin/upload_image', methods=['POST'])
def admin_upload_image():
    """
    Upload or replace the image for an existing product.
    Form fields: product_id (required), image (file, required).
    """
    try:
        product_id = request.form.get('product_id', '').strip()
        image_file = request.files.get('image')

        if not product_id:
            return jsonify({'success': False, 'message': 'product_id is required'}), 400

        try:
            filename, image_url = _save_image(image_file, product_id)
        except ValueError as ve:
            return jsonify({'success': False, 'message': str(ve)}), 400

        conn = getDatabaseConnection()
        try:
            cursor = conn.cursor()
            # Fetch old image filename to remove stale file
            cursor.execute(
                "SELECT image_filename FROM inventory WHERE item_name = %s OR id::TEXT = %s",
                (product_id, product_id),
            )
            row = cursor.fetchone()
            if not row:
                conn.close()
                # Clean up the just-saved file
                try:
                    os.remove(os.path.join(IMAGES_DIR, filename))
                except OSError:
                    pass
                return jsonify({'success': False, 'message': 'Product not found'}), 404

            old_filename = row[0]

            cursor.execute(
                "UPDATE inventory SET image_filename = %s, image_url = %s, updated_at = NOW() "
                "WHERE item_name = %s OR id::TEXT = %s",
                (filename, image_url, product_id, product_id),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

        # Remove old image if it exists and differs from the new one
        if old_filename and old_filename != filename:
            old_path = os.path.join(IMAGES_DIR, old_filename)
            try:
                if os.path.isfile(old_path):
                    os.remove(old_path)
            except OSError as oe:
                logger.warning("Could not remove old image '%s': %s", old_path, oe)

        get_publisher().publish_product_modified(product_id)

        return jsonify({'success': True, 'image_filename': filename, 'image_url': image_url})
    except Exception as e:
        logger.error("Admin Upload Image Error: %s", e)
        return jsonify({'success': False, 'message': str(e)}), 500