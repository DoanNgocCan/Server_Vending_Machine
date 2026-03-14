"""
Trang 03: Quản Lý Kho — Tồn kho theo từng máy.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
import pandas as pd

from utils.auth import check_authentication
from utils.api_client import (
    get_devices, get_all_products,
    get_device_inventory, add_stock, update_device_inventory,
)
from utils.helpers import format_datetime, stock_status_color

st.set_page_config(page_title="Kho Hàng — Vending Admin", page_icon="📦", layout="wide")

if not check_authentication():
    st.stop()

st.title("📦 Quản Lý Kho Hàng")

if st.button("🔄 Làm mới"):
    st.cache_data.clear()
    st.rerun()

# ── Fetch data ─────────────────────────────────────────────────────────────
with st.spinner("Đang tải..."):
    devices_resp = get_devices()
    products_resp = get_all_products()

devices = devices_resp.get("devices", []) if devices_resp.get("success") else []
products = products_resp.get("products", []) if products_resp.get("success") else []

if not devices:
    st.warning("⚠️ Chưa có máy nào trong hệ thống. Hãy đảm bảo thiết bị đã kết nối và đồng bộ.")
    st.stop()

if not products:
    st.warning("⚠️ Chưa có sản phẩm nào trong master data.")
    st.stop()

product_names = [p["item_name"] for p in products]
device_ids = [d["device_id"] for d in devices]

tab_view, tab_add, tab_set = st.tabs(["📋 Xem Kho", "➕ Nhập Hàng", "✏️ Đặt Số Lượng"])

# ════════════════════════════════════════════════════════
# TAB 1: XEM TỒN KHO
# ════════════════════════════════════════════════════════
with tab_view:
    st.subheader("📋 Tồn Kho Theo Máy")

    # Tổng quan thiết bị
    df_dev = pd.DataFrame(devices)
    show_cols = [c for c in ["device_id", "product_count", "total_units", "last_sync"] if c in df_dev.columns]
    if "last_sync" in df_dev.columns:
        df_dev["last_sync"] = df_dev["last_sync"].apply(format_datetime)
    st.dataframe(df_dev[show_cols], use_container_width=True,
                 column_config={
                     "device_id": st.column_config.TextColumn("ID Máy"),
                     "product_count": st.column_config.NumberColumn("Số loại SP"),
                     "total_units": st.column_config.NumberColumn("Tổng tồn kho"),
                     "last_sync": st.column_config.TextColumn("Đồng bộ lần cuối"),
                 })

    st.markdown("---")

    # Chi tiết từng máy
    sel_dev = st.selectbox("Chọn máy để xem chi tiết:", device_ids, key="view_device")
    if sel_dev:
        with st.spinner(f"Đang tải kho của {sel_dev}..."):
            inv_resp = get_device_inventory(sel_dev)

        if inv_resp.get("success"):
            items = inv_resp.get("inventory", [])
            if items:
                df_inv = pd.DataFrame(items)
                if "last_updated" in df_inv.columns:
                    df_inv["last_updated"] = df_inv["last_updated"].apply(format_datetime)
                df_inv["trạng_thái"] = df_inv["units_left"].apply(stock_status_color)

                st.dataframe(
                    df_inv[[c for c in ["item_name", "units_left", "trạng_thái", "price", "custom_price", "last_updated"] if c in df_inv.columns]],
                    use_container_width=True,
                    column_config={
                        "item_name": st.column_config.TextColumn("Sản phẩm"),
                        "units_left": st.column_config.NumberColumn("Tồn kho"),
                        "trạng_thái": st.column_config.TextColumn("Mức độ"),
                        "price": st.column_config.NumberColumn("Giá gốc (₫)", format="%,.0f"),
                        "custom_price": st.column_config.NumberColumn("Giá riêng (₫)", format="%,.0f"),
                    },
                )
            else:
                st.info(f"Máy {sel_dev} chưa có sản phẩm nào trong kho.")
        else:
            st.error(f"❌ {inv_resp.get('message')}")

# ════════════════════════════════════════════════════════
# TAB 2: NHẬP HÀNG (Cộng thêm vào kho)
# ════════════════════════════════════════════════════════
with tab_add:
    st.subheader("➕ Nhập Hàng Vào Kho Máy")
    st.info("💡 Nhập hàng sẽ **cộng thêm** vào số lượng hiện có.")

    with st.form("add_stock_form"):
        dev = st.selectbox("Máy bán hàng:", device_ids, key="add_dev")
        prod = st.selectbox("Sản phẩm:", product_names, key="add_prod")
        qty = st.number_input("Số lượng nhập thêm:", min_value=1, step=1, value=10)
        submitted = st.form_submit_button("➕ Nhập Hàng", type="primary")

        if submitted:
            with st.spinner("Đang cập nhật..."):
                result = add_stock(dev, prod, qty)
            if result.get("success"):
                st.success(f"✅ {result.get('message', 'Nhập hàng thành công!')}")
                st.cache_data.clear()
            else:
                st.error(f"❌ {result.get('message')}")

# ════════════════════════════════════════════════════════
# TAB 3: ĐẶT SỐ LƯỢNG CHÍNH XÁC
# ════════════════════════════════════════════════════════
with tab_set:
    st.subheader("✏️ Đặt Số Lượng Tồn Kho Chính Xác")
    st.warning("⚠️ Thao tác này sẽ **ghi đè** số lượng hiện tại!")

    col_dev, col_prod = st.columns(2)
    with col_dev:
        set_dev = st.selectbox("Máy:", device_ids, key="set_dev")
    with col_prod:
        set_prod = st.selectbox("Sản phẩm:", product_names, key="set_prod")

    # Hiển thị tồn kho hiện tại
    if set_dev and set_prod:
        inv_r = get_device_inventory(set_dev)
        current_qty = 0
        if inv_r.get("success"):
            for item in inv_r.get("inventory", []):
                if item.get("item_name") == set_prod:
                    current_qty = item.get("units_left", 0)
                    break
        st.info(f"Tồn kho hiện tại của **{set_prod}** tại **{set_dev}**: **{current_qty}**")

    with st.form("set_stock_form"):
        new_qty = st.number_input("Số lượng mới:", min_value=0, step=1, value=0)
        submitted2 = st.form_submit_button("💾 Cập Nhật", type="primary")

        if submitted2:
            with st.spinner("Đang cập nhật..."):
                result2 = update_device_inventory(set_dev, set_prod, new_qty)
            if result2.get("success"):
                st.success(f"✅ {result2.get('message')}")
                st.cache_data.clear()
                st.rerun()
            else:
                st.error(f"❌ {result2.get('message')}")
