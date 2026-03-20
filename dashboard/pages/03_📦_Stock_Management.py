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
    # Thay thế đoạn code hiển thị dataframe cũ thành đoạn này:
    st.dataframe(
        df_inv[[c for c in ["slot_number", "item_name", "units_left", "trạng_thái", "price", "custom_price", "last_updated"] if c in df_inv.columns]],
        use_container_width=True,
        column_config={
            "slot_number": st.column_config.NumberColumn("Số ô"), # <-- Cột mới
            "item_name": st.column_config.TextColumn("Sản phẩm"),
            "units_left": st.column_config.NumberColumn("Tồn kho"),
            "trạng_thái": st.column_config.TextColumn("Mức độ"),
            "price": st.column_config.NumberColumn("Giá gốc (₫)", format="%,.0f"),
            "custom_price": st.column_config.NumberColumn("Giá riêng (₫)", format="%,.0f"),
        },
    )

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
    st.subheader("✏️ Đặt Số Lượng & Quản Lý Cục Bộ")
    st.warning("⚠️ Thao tác ở đây chỉ ảnh hưởng đến máy được chọn, không ảnh hưởng đến Master Data.")

    col_dev, col_prod = st.columns(2)
    with col_dev:
        set_dev = st.selectbox("Chọn Máy:", device_ids, key="set_dev")
    with col_prod:
        set_prod = st.selectbox("Chọn Sản phẩm:", product_names, key="set_prod")

    # Hiển thị tồn kho hiện tại
    current_qty = 0
    current_slot = 1  # <-- Thêm biến này
    is_in_device = False
    
    if set_dev and set_prod:
        inv_r = get_device_inventory(set_dev)
        if inv_r.get("success"):
            for item in inv_r.get("inventory", []):
                if item.get("item_name") == set_prod:
                    current_qty = item.get("units_left", 0)
                    current_slot = item.get("slot_number") or 1 # <-- Lấy số ô hiện tại
                    is_in_device = True
                    break
                    
        if is_in_device:
            st.info(f"Sản phẩm **{set_prod}** đang có ở máy **{set_dev}** tại Ô SỐ: **{current_slot}** (Số lượng: {current_qty})")
        else:
            st.info(f"Sản phẩm **{set_prod}** hiện KHÔNG CÓ TRONG KHO của máy **{set_dev}**.")

    st.markdown("---")
    
    c1, c2 = st.columns(2)
    
    with c1:
        with st.form("set_stock_form"):
            st.markdown("**🔄 Cập nhật số lượng & Ô**")
            new_qty = st.number_input("Số lượng mới:", min_value=0, step=1, value=current_qty)
            # Thêm selectbox chọn ô vào form này
            new_slot = st.selectbox("Số ô hiển thị trên máy (1-10):", options=list(range(1, 11)), index=current_slot-1)
            
            submitted2 = st.form_submit_button("💾 Lưu Thay Đổi", type="primary")

            if submitted2:
                with st.spinner("Đang cập nhật..."):
                    # CHÚ Ý: Đã truyền đủ 4 biến vào đây
                    result2 = update_device_inventory(set_dev, set_prod, new_qty, new_slot)
                if result2.get("success"):
                    st.success(f"✅ {result2.get('message', 'Cập nhật thành công!')}")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error(f"❌ {result2.get('message')}")

    with c2:
        st.markdown("**🗑️ Gỡ sản phẩm khỏi máy**")
        st.caption("Sản phẩm sẽ biến mất khỏi màn hình của máy này.")
        
        # Chỉ hiện nút gỡ nếu sản phẩm thực sự đang có trong máy đó
        if is_in_device:
            if st.button("🗑️ Gỡ khỏi máy này", type="secondary", use_container_width=True):
                st.session_state["confirm_remove_device"] = f"{set_dev}_{set_prod}"
                
            if st.session_state.get("confirm_remove_device") == f"{set_dev}_{set_prod}":
                st.error(f"Xác nhận gỡ **{set_prod}** khỏi **{set_dev}**?")
                col_y, col_n = st.columns(2)
                with col_y:
                    if st.button("✅ Đồng ý"):
                        # Import hàm remove vừa viết ở api_client (Nhớ import ở đầu file nhé)
                        from utils.api_client import remove_product_from_device
                        res = remove_product_from_device(set_dev, set_prod)
                        
                        if res.get("success"):
                            st.success("✅ Đã gỡ thành công!")
                            st.session_state.pop("confirm_remove_device", None)
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.error(f"❌ Lỗi: {res.get('message')}")
                with col_n:
                    if st.button("❌ Hủy"):
                        st.session_state.pop("confirm_remove_device", None)
                        st.rerun()
        else:
            st.button("🚫 Không thể gỡ (Chưa có trong máy)", disabled=True, use_container_width=True)
