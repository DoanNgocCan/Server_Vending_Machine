# dashboard/main.py — Entry point của Admin Dashboard
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
from utils.auth import check_authentication, logout, get_username

st.set_page_config(
    page_title="Vending Machine Admin",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

if not check_authentication():
    st.stop()

# ── Sidebar ──────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/color/96/vending-machine.png", width=80)
    st.markdown("### 🤖 Vending Machine Admin")
    st.divider()
    col1, col2 = st.columns([3, 1])
    with col1:
        st.write(f"👤 **{get_username()}**")
    with col2:
        if st.button("🚪", help="Đăng xuất"):
            logout()
    st.divider()
    st.info("Chọn trang từ menu bên trái để quản lý hệ thống.")

# ── Home page content ─────────────────────────
st.title("🤖 Vending Machine Admin Dashboard")
st.markdown("Chào mừng đến với hệ thống quản trị máy bán hàng tự động.")
st.markdown("---")

col1, col2, col3 = st.columns(3)
with col1:
    st.info("### 📊 Dashboard\nXem tổng quan KPI và trạng thái hệ thống.")
with col2:
    st.info("### 📦 Sản Phẩm\nQuản lý sản phẩm, giá cả và hình ảnh.")
with col3:
    st.info("### 📈 Kho & Phân Tích\nQuản lý tồn kho và xem báo cáo doanh thu.")

st.markdown("---")
st.caption("Sử dụng menu điều hướng bên trái để bắt đầu.")