"""
Trang 01: Dashboard Overview — Tổng quan hệ thống.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

from utils.auth import check_authentication
from utils.api_client import get_all_products, get_devices, get_transactions, get_inventory_stats, get_device_inventory
from utils.helpers import format_currency, format_number, format_datetime, stock_status_color

st.set_page_config(page_title="Dashboard — Vending Admin", page_icon="📊", layout="wide")

if not check_authentication():
    st.stop()

st.title("📊 Dashboard Tổng Quan")
st.caption(f"Cập nhật lúc: {datetime.now().strftime('%H:%M %d/%m/%Y')}")

if st.button("🔄 Làm mới dữ liệu"):
    st.cache_data.clear()
    st.rerun()

# ── Fetch data ─────────────────────────────────────────────────────────────
with st.spinner("Đang tải dữ liệu..."):
    products_resp = get_all_products()
    devices_resp = get_devices()
    trans_resp = get_transactions(limit=500)
    stats_resp = get_inventory_stats()

products = products_resp.get("products", []) if products_resp.get("success") else []
devices = devices_resp.get("devices", []) if devices_resp.get("success") else []
transactions = trans_resp.get("transactions", []) if trans_resp.get("success") else []
stats = stats_resp.get("stats", {}) if stats_resp.get("success") else {}

df_trans = pd.DataFrame(transactions) if transactions else pd.DataFrame()

# ── KPI Cards ──────────────────────────────────────────────────────────────
st.markdown("### 📌 Chỉ Số Tổng Quan")
k1, k2, k3, k4 = st.columns(4)

total_revenue = df_trans["total_amount"].sum() if not df_trans.empty and "total_amount" in df_trans.columns else 0
k1.metric("💰 Tổng Doanh Thu", format_currency(total_revenue))
k2.metric("📦 Sản Phẩm", len(products))
k3.metric("🖥️ Máy Kết Nối", len(devices))
k4.metric("🧾 Tổng Giao Dịch", format_number(len(transactions)))

st.markdown("---")

# ── Charts ─────────────────────────────────────────────────────────────────
left, right = st.columns(2)

with left:
    st.subheader("📈 Doanh Thu Theo Ngày")
    if not df_trans.empty and "created_at" in df_trans.columns:
        df_trans["date"] = pd.to_datetime(df_trans["created_at"]).dt.date
        daily = df_trans.groupby("date")["total_amount"].sum().reset_index()
        fig = px.line(daily, x="date", y="total_amount",
                      labels={"date": "Ngày", "total_amount": "Doanh Thu (₫)"},
                      markers=True)
        fig.update_layout(margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Chưa có dữ liệu giao dịch.")

with right:
    st.subheader("🏆 Top Sản Phẩm Bán Chạy")
    if stats:
        df_stats = pd.DataFrame(list(stats.items()), columns=["Sản phẩm", "Đã bán"])
        df_stats = df_stats.sort_values("Đã bán", ascending=False).head(10)
        fig2 = px.bar(df_stats, x="Đã bán", y="Sản phẩm", orientation="h",
                      color="Đã bán", color_continuous_scale="Reds")
        fig2.update_layout(margin=dict(l=0, r=0, t=30, b=0), showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Chưa có dữ liệu thống kê.")

st.markdown("---")

# ── Low Stock Alerts ────────────────────────────────────────────────────────
st.subheader("⚠️ Cảnh Báo Tồn Kho Thấp")
if devices:
    low_stock_rows = []
    for dev in devices:
        dev_id = dev.get("device_id", "")
        inv_resp = get_device_inventory(dev_id)
        if inv_resp.get("success"):
            for item in inv_resp.get("inventory", []):
                ul = item.get("units_left", 0)
                if ul < 10:
                    low_stock_rows.append({
                        "Máy": dev_id,
                        "Sản phẩm": item.get("item_name"),
                        "Tồn kho": ul,
                        "Trạng thái": stock_status_color(ul),
                    })
    if low_stock_rows:
        st.dataframe(pd.DataFrame(low_stock_rows), use_container_width=True)
    else:
        st.success("✅ Tất cả sản phẩm đều có tồn kho đủ (≥ 10).")
else:
    st.info("Chưa có máy nào được kết nối.")

# ── Recent Transactions ─────────────────────────────────────────────────────
st.subheader("📋 Giao Dịch Gần Nhất")
if not df_trans.empty:
    cols_show = [c for c in ["transaction_id", "device_id", "total_amount", "payment_status", "created_at"] if c in df_trans.columns]
    display = df_trans[cols_show].head(10).copy()
    if "total_amount" in display.columns:
        display["total_amount"] = display["total_amount"].apply(format_currency)
    if "created_at" in display.columns:
        display["created_at"] = display["created_at"].apply(format_datetime)
    st.dataframe(display, use_container_width=True)
else:
    st.info("Chưa có giao dịch nào.")
