"""
Trang 04: Quản Lý Giá — Giá toàn cầu và giá riêng theo máy.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
import pandas as pd

from utils.auth import check_authentication
from utils.api_client import get_all_products, get_devices, update_product, set_custom_price
from utils.helpers import format_currency

st.set_page_config(page_title="Giá Cả — Vending Admin", page_icon="💰", layout="wide")

if not check_authentication():
    st.stop()

st.title("💰 Quản Lý Giá")

if st.button("🔄 Làm mới"):
    st.cache_data.clear()
    st.rerun()

# ── Fetch data ─────────────────────────────────────────────────────────────
with st.spinner("Đang tải..."):
    products_resp = get_all_products()
    devices_resp = get_devices()

products = products_resp.get("products", []) if products_resp.get("success") else []
devices = devices_resp.get("devices", []) if devices_resp.get("success") else []

if not products:
    st.warning("Chưa có sản phẩm nào.")
    st.stop()

product_names = [p["item_name"] for p in products]
device_ids = [d["device_id"] for d in devices]

tab_global, tab_device, tab_bulk = st.tabs(["🌐 Giá Toàn Hệ Thống", "🖥️ Giá Riêng Theo Máy", "📊 Xem Bảng Giá"])

# ════════════════════════════════════════════════════════
# TAB 1: CẬP NHẬT GIÁ TOÀN HỆ THỐNG
# ════════════════════════════════════════════════════════
with tab_global:
    st.subheader("🌐 Cập Nhật Giá Toàn Hệ Thống")
    st.info("💡 Thay đổi này sẽ ảnh hưởng đến tất cả máy (trừ máy có giá riêng).")

    df_prod = pd.DataFrame(products)

    with st.form("global_price_form"):
        sel_prod = st.selectbox("Chọn sản phẩm:", product_names)
        cur_price = 0.0
        if sel_prod:
            row = df_prod[df_prod["item_name"] == sel_prod]
            if not row.empty:
                cur_price = float(row.iloc[0].get("price", 0))

        st.info(f"Giá hiện tại: **{format_currency(cur_price)}**")

        new_price = st.number_input("Giá mới (₫):", min_value=0.0, step=1000.0, value=cur_price)
        discount_pct = st.slider("Hoặc giảm giá (%):", min_value=0, max_value=90, value=0)

        if discount_pct > 0:
            discounted = cur_price * (1 - discount_pct / 100)
            st.info(f"Giá sau khi giảm {discount_pct}%: **{format_currency(discounted)}**")
            effective_price = discounted
        else:
            effective_price = new_price

        submitted = st.form_submit_button("💾 Cập Nhật Giá Toàn Hệ Thống", type="primary")
        if submitted:
            if effective_price <= 0:
                st.error("❌ Giá phải lớn hơn 0!")
            else:
                with st.spinner("Đang cập nhật..."):
                    result = update_product(old_name=sel_prod, price=effective_price)
                if result.get("success"):
                    st.success(f"✅ Đã cập nhật giá {sel_prod} → {format_currency(effective_price)}")
                    st.cache_data.clear()
                else:
                    st.error(f"❌ {result.get('message')}")

# ════════════════════════════════════════════════════════
# TAB 2: GIÁ RIÊNG THEO MÁY
# ════════════════════════════════════════════════════════
with tab_device:
    st.subheader("🖥️ Đặt Giá Riêng Cho Từng Máy")
    st.info("💡 Giá riêng này sẽ ghi đè giá toàn hệ thống tại máy được chọn.")

    if not device_ids:
        st.warning("Chưa có máy nào trong hệ thống.")
    else:
        with st.form("device_price_form"):
            dev_sel = st.selectbox("Chọn máy:", device_ids, key="dp_dev")
            prod_sel = st.selectbox("Chọn sản phẩm:", product_names, key="dp_prod")

            global_price = 0.0
            if prod_sel:
                row = df_prod[df_prod["item_name"] == prod_sel]
                if not row.empty:
                    global_price = float(row.iloc[0].get("price", 0))
            st.info(f"Giá toàn hệ thống: **{format_currency(global_price)}**")

            device_price = st.number_input("Giá riêng tại máy này (₫):", min_value=0.0, step=1000.0, value=global_price)
            diff = device_price - global_price
            if diff > 0:
                st.caption(f"↑ Cao hơn giá gốc: {format_currency(diff)}")
            elif diff < 0:
                st.caption(f"↓ Thấp hơn giá gốc: {format_currency(abs(diff))}")

            sub2 = st.form_submit_button("💾 Lưu Giá Riêng", type="primary")
            if sub2:
                if device_price <= 0:
                    st.error("❌ Giá phải lớn hơn 0!")
                else:
                    with st.spinner("Đang cập nhật..."):
                        result2 = set_custom_price(dev_sel, prod_sel, device_price)
                    if result2.get("success"):
                        st.success(f"✅ Đã đặt giá riêng {prod_sel} tại {dev_sel}: {format_currency(device_price)}")
                        st.cache_data.clear()
                    else:
                        st.error(f"❌ {result2.get('message')}")

# ════════════════════════════════════════════════════════
# TAB 3: XEM BẢNG GIÁ
# ════════════════════════════════════════════════════════
with tab_bulk:
    st.subheader("📊 Bảng Giá Master Data")
    if products:
        df_show = pd.DataFrame(products)
        show_cols = [c for c in ["item_name", "price", "cost_price", "description"] if c in df_show.columns]
        st.dataframe(
            df_show[show_cols],
            use_container_width=True,
            column_config={
                "item_name": st.column_config.TextColumn("Sản phẩm"),
                "price": st.column_config.NumberColumn("Giá bán (₫)", format="%,.0f"),
                "cost_price": st.column_config.NumberColumn("Giá vốn (₫)", format="%,.0f"),
                "description": st.column_config.TextColumn("Mô tả"),
            },
        )

        # Tính lợi nhuận gộp
        if "price" in df_show.columns and "cost_price" in df_show.columns:
            df_show["lợi_nhuận"] = df_show["price"] - df_show["cost_price"]
            df_show["biên_lợi_nhuận_%"] = (df_show["lợi_nhuận"] / df_show["price"].replace(0, float("nan")) * 100).round(1)
            st.markdown("**💡 Phân Tích Lợi Nhuận Gộp:**")
            st.dataframe(
                df_show[["item_name", "price", "cost_price", "lợi_nhuận", "biên_lợi_nhuận_%"]],
                use_container_width=True,
            )
