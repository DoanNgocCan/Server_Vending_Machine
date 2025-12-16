# dashboard/services.py
import requests
import streamlit as st
import pandas as pd

# API_URL = "http://localhost:5000" # Dùng local khi dev
API_URL = "https://rpi.vietseedscampaign.com" # Dùng domain thật

@st.cache_data(ttl=60) # Giảm cache xuống 1 phút để cập nhật nhanh hơn
def fetch_all_transactions():
    try:
        response = requests.get(f"{API_URL}/api/transactions?limit=10000")
        if response.status_code == 200:
            return response.json().get('transactions', [])
        return []
    except Exception: return []

@st.cache_data(ttl=60)
def fetch_products(device_id=None):
    """
    Lấy danh sách sản phẩm.
    Nếu có device_id -> Lấy kèm tồn kho của máy đó.
    Nếu không -> Lấy Master Data (không có tồn kho).
    """
    try:
        headers = {}
        if device_id:
            headers = {"X-Device-ID": device_id}
            
        response = requests.get(f"{API_URL}/api/products", headers=headers)
        if response.status_code == 200:
            return response.json().get('products', [])
        return []
    except Exception: return []

@st.cache_data(ttl=60)
def fetch_users():
    try:
        response = requests.get(f"{API_URL}/api/users?limit=1000")
        if response.status_code == 200:
            return response.json().get('users', [])
        return []
    except Exception: return []

def update_product_info(old_name, new_name, price, add_stock, device_id):
    """Gọi API Admin để cập nhật sản phẩm"""
    payload = {
        "old_name": old_name,
        "new_name": new_name,
        "price": price,
        "add_stock": add_stock,
        "device_id": device_id
    }
    try:
        resp = requests.post(f"{API_URL}/api/admin/update_product", json=payload)
        return resp.status_code == 200, resp.json().get('message')
    except Exception as e:
        return False, str(e)