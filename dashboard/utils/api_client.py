"""
API Client - Giao tiếp với Flask Server backend.
Tất cả các trang Streamlit sẽ dùng module này để gọi API.
"""
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import SERVER_URL, API_TIMEOUT

logger = logging.getLogger(__name__)


def _make_session():
    """Tạo requests.Session với retry tự động."""
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


_session = _make_session()


def _get(path, params=None, headers=None):
    try:
        url = f"{SERVER_URL}{path}"
        resp = _session.get(url, params=params, headers=headers, timeout=API_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        logger.error(f"Connection error: {path}")
        return {"success": False, "message": "Không thể kết nối tới server"}
    except requests.exceptions.Timeout:
        logger.error(f"Timeout: {path}")
        return {"success": False, "message": "Server phản hồi quá chậm"}
    except Exception as e:
        logger.error(f"GET {path} error: {e}")
        return {"success": False, "message": str(e)}


def _post(path, json=None, data=None, files=None):
    try:
        url = f"{SERVER_URL}{path}"
        resp = _session.post(url, json=json, data=data, files=files, timeout=API_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        return {"success": False, "message": "Không thể kết nối tới server"}
    except requests.exceptions.Timeout:
        return {"success": False, "message": "Server phản hồi quá chậm"}
    except Exception as e:
        logger.error(f"POST {path} error: {e}")
        return {"success": False, "message": str(e)}


def _put(path, json=None):
    try:
        url = f"{SERVER_URL}{path}"
        resp = _session.put(url, json=json, timeout=API_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        return {"success": False, "message": "Không thể kết nối tới server"}
    except Exception as e:
        logger.error(f"PUT {path} error: {e}")
        return {"success": False, "message": str(e)}


def _delete(path):
    try:
        url = f"{SERVER_URL}{path}"
        resp = _session.delete(url, timeout=API_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        return {"success": False, "message": "Không thể kết nối tới server"}
    except Exception as e:
        logger.error(f"DELETE {path} error: {e}")
        return {"success": False, "message": str(e)}


# ──────────────────────────────────────────────
# PRODUCTS
# ──────────────────────────────────────────────

def get_all_products():
    """GET /api/products — lấy master data (không có tồn kho)."""
    return _get("/api/products")


def get_products_for_device(device_id):
    """GET /api/products với X-Device-ID header — có tồn kho."""
    return _get("/api/products", headers={"X-Device-ID": device_id})


def create_product(item_name, price, cost_price=0, description=""):
    """POST /api/admin/create_product"""
    return _post("/api/admin/create_product", json={
        "item_name": item_name,
        "price": price,
        "cost_price": cost_price,
        "description": description,
    })


def update_product(old_name, new_name=None, price=None, add_stock=0, device_id=None):
    """POST /api/admin/update_product"""
    payload = {"old_name": old_name}
    if new_name:
        payload["new_name"] = new_name
    if price is not None:
        payload["price"] = price
    if add_stock:
        payload["add_stock"] = add_stock
    if device_id:
        payload["device_id"] = device_id
    return _post("/api/admin/update_product", json=payload)


def delete_product(item_name):
    """DELETE /api/admin/products/<item_name>"""
    return _delete(f"/api/admin/products/{item_name}")


# ──────────────────────────────────────────────
# DEVICES
# ──────────────────────────────────────────────

def get_devices():
    """GET /api/devices"""
    return _get("/api/devices")


def add_stock(device_id, item_name, quantity):
    """POST /api/admin/add_stock"""
    return _post("/api/admin/add_stock", json={
        "device_id": device_id,
        "item_name": item_name,
        "quantity": quantity,
    })


def get_device_inventory(device_id):
    """GET /api/devices/<device_id>/inventory"""
    return _get(f"/api/devices/{device_id}/inventory")


# Ví dụ sửa trong utils/api_client.py
def update_device_inventory(device_id, item_name, units_left, slot_number):
    """PUT /api/devices/<device_id>/inventory/<item_name>"""
    payload = {
        "units_left": units_left,
        "slot_number": slot_number  # <-- Đã thêm số ô
    }
    # Dùng _put thay vì requests.put để tận dụng Retry và SERVER_URL mặc định
    return _put(f"/api/devices/{device_id}/inventory/{item_name}", json=payload)


def set_custom_price(device_id, item_name, price):
    """POST /api/products/set_custom"""
    return _post("/api/products/set_custom", json={
        "device_id": device_id,
        "item_name": item_name,
        "price": price,
    })
def remove_product_from_device(device_id, item_name):
    """DELETE /api/devices/<device_id>/inventory/<item_name> - Gỡ sản phẩm khỏi 1 máy cụ thể"""
    return _delete(f"/api/devices/{device_id}/inventory/{item_name}")

# ──────────────────────────────────────────────
# TRANSACTIONS
# ──────────────────────────────────────────────

def get_transactions(limit=20, offset=0, device_id=None, user_id=None):
    """GET /api/transactions"""
    params = {"limit": limit, "offset": offset}
    if device_id:
        params["device_id"] = device_id
    if user_id:
        params["user_id"] = user_id
    return _get("/api/transactions", params=params)


def get_inventory_stats():
    """GET /api/inventory/stats"""
    return _get("/api/inventory/stats")


# ──────────────────────────────────────────────
# IMAGES
# ──────────────────────────────────────────────

def upload_image(item_name, file_bytes, filename):
    """POST /api/admin/upload_image (multipart)"""
    files = {"image": (filename, file_bytes)}
    data = {"item_name": item_name}
    return _post("/api/admin/upload_image", data=data, files=files)


def get_image_url(image_url_path):
    """Trả về full URL của ảnh."""
    if not image_url_path:
        return None
    if image_url_path.startswith("http"):
        return image_url_path
    return f"{SERVER_URL}{image_url_path}"


# ──────────────────────────────────────────────
# USERS
# ──────────────────────────────────────────────

def get_users(limit=20, offset=0, search=None):
    """GET /api/users"""
    params = {"limit": limit, "offset": offset}
    if search:
        params["search"] = search
    return _get("/api/users", params=params)
