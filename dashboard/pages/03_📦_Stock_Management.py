"""
Trang 03: Quản Lý Kho — Xem tổng quan và chi tiết tồn kho theo từng máy / toàn hệ thống.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
import pandas as pd

from utils.auth import check_authentication
from utils.api_client import get_devices, get_all_products, get_device_inventory
from utils.helpers import format_datetime, stock_status_color

st.set_page_config(page_title="Kho Hàng — Vending Admin", page_icon="📦", layout="wide")

if not check_authentication():
    st.stop()

st.title("📦 Giám Sát Tồn Kho")

if st.button("🔄 Làm mới dữ liệu"):
    st.cache_data.clear()
    st.rerun()

# ── Fetch data ─────────────────────────────────────────────────────────────
with st.spinner("Đang tải dữ liệu hệ thống..."):
    devices_resp = get_devices()
    products_resp = get_all_products()

devices = devices_resp.get("devices", []) if devices_resp.get("success") else []
products = products_resp.get("products", []) if products_resp.get("success") else []

if not devices:
    st.warning("⚠️ Chưa có máy nào trong hệ thống. Hãy đảm bảo thiết bị đã kết nối và đồng bộ.")
    st.stop()

# Tải toàn bộ tồn kho của tất cả các máy để gom chung vào 1 bảng
all_inventory = []
with st.spinner("Đang tải dữ liệu tồn kho chi tiết..."):
    for dev in devices:
        dev_id = dev.get("device_id")
        inv_resp = get_device_inventory(dev_id)
        if inv_resp.get("success"):
            items = inv_resp.get("inventory", [])
            for item in items:
                item["device_id"] = dev_id
                all_inventory.append(item)

df_inv = pd.DataFrame(all_inventory)

# ════════════════════════════════════════════════════════
# PHẦN 1: TỔNG QUAN HỆ THỐNG
# ════════════════════════════════════════════════════════
st.markdown("### 📌 Tổng Quan Hệ Thống")
k1, k2, k3 = st.columns(3)
k1.metric("🖥️ Tổng số máy kết nối", len(devices))
k2.metric("📦 Mẫu sản phẩm (Master Data)", len(products))
total_units = df_inv["units_left"].sum() if not df_inv.empty else 0
k3.metric("🧮 Tổng sản phẩm đang tồn (Toàn hệ thống)", f"{total_units:,.0f}")

st.markdown("---")

# ════════════════════════════════════════════════════════
# PHẦN 2: TRA CỨU TỒN KHO CHI TIẾT VÀ BỘ LỌC
# ════════════════════════════════════════════════════════
st.subheader("🔍 Tra Cứu Tồn Kho Chi Tiết")

col_filter1, col_filter2 = st.columns(2)
with col_filter1:
    device_ids = [d["device_id"] for d in devices]
    selected_devices = st.multiselect("🖥️ Lọc theo máy:", options=device_ids, default=device_ids)
with col_filter2:
    product_names = [p["item_name"] for p in products]
    selected_products = st.multiselect("📦 Lọc theo sản phẩm (Để trống để xem tất cả):", options=product_names, default=[])

if not df_inv.empty:
    # Áp dụng bộ lọc
    filtered_df = df_inv[df_inv["device_id"].isin(selected_devices)].copy()
    if selected_products:
        filtered_df = filtered_df[filtered_df["item_name"].isin(selected_products)]

    if not filtered_df.empty:
        # Xử lý format dữ liệu trước khi hiển thị
        if "last_updated" in filtered_df.columns:
            filtered_df["last_updated"] = filtered_df["last_updated"].apply(format_datetime)
        
        filtered_df["trạng_thái"] = filtered_df["units_left"].apply(stock_status_color)

        # Chọn các cột cần hiển thị
        show_cols = ["device_id", "slot_number", "item_name", "units_left", "trạng_thái", "price", "custom_price", "last_updated"]
        show_cols = [c for c in show_cols if c in filtered_df.columns]

        tab_detail, tab_summary = st.tabs(["📋 Chi Tiết Từng Ô Thuộc Máy", "📊 Tổng Hợp Theo Sản Phẩm"])
        
        with tab_detail:
            st.dataframe(
                filtered_df[show_cols],
                use_container_width=True,
                column_config={
                    "device_id": st.column_config.TextColumn("Mã Máy"),
                    "slot_number": st.column_config.NumberColumn("Số Ô"),
                    "item_name": st.column_config.TextColumn("Sản phẩm"),
                    "units_left": st.column_config.NumberColumn("Tồn kho"),
                    "trạng_thái": st.column_config.TextColumn("Cảnh báo"),
                    "price": st.column_config.NumberColumn("Giá Bán Chung (₫)", format="%,.0f"), # <-- Đổi từ "Giá gốc" thành "Giá Bán Chung"
                    "custom_price": st.column_config.NumberColumn("Giá Máy Này (₫)", format="%,.0f"), # <-- Làm rõ ràng hơn
                    "last_updated": st.column_config.TextColumn("Cập nhật lần cuối"),
                },
            )

        with tab_summary:
            st.info("💡 Bảng này cộng dồn số lượng tồn của từng mặt hàng dựa trên các máy bạn đang chọn ở bộ lọc phía trên.")
            agg_df = filtered_df.groupby("item_name")["units_left"].sum().reset_index()
            agg_df.columns = ["Tên Sản Phẩm", "Tổng Tồn Kho (Đang chọn)"]
            agg_df = agg_df.sort_values("Tổng Tồn Kho (Đang chọn)", ascending=False)
            
            st.dataframe(
                agg_df, 
                use_container_width=True,
                column_config={
                    "Tên Sản Phẩm": st.column_config.TextColumn("Tên Sản Phẩm"),
                    "Tổng Tồn Kho (Đang chọn)": st.column_config.NumberColumn("Tổng Tồn Kho"),
                }
            )

    else:
        st.warning("Không có dữ liệu tồn kho nào phù hợp với bộ lọc hiện tại.")
else:
    st.info("Hiện tại kho của tất cả các máy đều đang trống.")