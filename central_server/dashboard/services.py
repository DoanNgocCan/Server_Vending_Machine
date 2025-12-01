# dashboard/services.py
import requests
import streamlit as st

API_URL = "http://rpi.vietseedscampaign.com" # Địa chỉ app.py đang chạy

@st.cache_data(ttl=300) # Cache 5 phút
def fetch_all_transactions():
    """
    Lấy toàn bộ lịch sử giao dịch.
    Lưu ý: setup limit thật lớn để lấy hết data cho biểu đồ
    """
    try:
        # Gọi API với limit lớn (ví dụ 10.000) để lấy hết lịch sử
        response = requests.get(f"{API_URL}/api/transactions?limit=10000")
        if response.status_code == 200:
            return response.json().get('transactions', [])
        return []
    except Exception as e:
        st.error(f"Lỗi kết nối API Transactions: {e}")
        return []

@st.cache_data(ttl=300)
def fetch_products():
    """Lấy danh sách sản phẩm để đếm số lượng"""
    try:
        # Header giả lập Device ID để lấy giá (không quan trọng lắm cho dashboard tổng)
        headers = {"X-Device-ID": "DASHBOARD_VIEWER"}
        response = requests.get(f"{API_URL}/api/products", headers=headers)
        if response.status_code == 200:
            return response.json().get('products', [])
        return []
    except Exception:
        return []

@st.cache_data(ttl=300)
def fetch_users():
    """Lấy danh sách user"""
    try:
        response = requests.get(f"{API_URL}/api/users?limit=10000")
        if response.status_code == 200:
            return response.json().get('users', [])
        return []
    except Exception:
        return []