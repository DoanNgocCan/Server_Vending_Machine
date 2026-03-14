"""
Trang 06: Phân Tích Doanh Thu — Sales analytics.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
import pandas as pd
import plotly.express as px
import json
from datetime import date, timedelta

from utils.auth import check_authentication
from utils.api_client import get_transactions, get_inventory_stats, get_devices
from utils.helpers import format_currency, format_number, format_datetime

st.set_page_config(page_title="Phân Tích — Vending Admin", page_icon="📊", layout="wide")

if not check_authentication():
    st.stop()

st.title("📊 Phân Tích Doanh Thu")

# ── Date range ─────────────────────────────────────────────────────────────
col_date1, col_date2, col_reload = st.columns([2, 2, 1])
with col_date1:
    start_date = st.date_input("Từ ngày:", value=date.today() - timedelta(days=30))
with col_date2:
    end_date = st.date_input("Đến ngày:", value=date.today())
with col_reload:
    st.write("")
    if st.button("🔄 Làm mới"):
        st.cache_data.clear()
        st.rerun()

# ── Fetch ──────────────────────────────────────────────────────────────────
with st.spinner("Đang tải dữ liệu..."):
    trans_resp = get_transactions(limit=5000)
    stats_resp = get_inventory_stats()
    devices_resp = get_devices()

transactions = trans_resp.get("transactions", []) if trans_resp.get("success") else []
stats = stats_resp.get("stats", {}) if stats_resp.get("success") else {}
devices = devices_resp.get("devices", []) if devices_resp.get("success") else []

if not transactions:
    st.info("Chưa có dữ liệu giao dịch nào.")
    st.stop()

df = pd.DataFrame(transactions)
df["created_at"] = pd.to_datetime(df["created_at"])
df["date"] = df["created_at"].dt.date

# Filter by date
df = df[(df["date"] >= start_date) & (df["date"] <= end_date)]

if df.empty:
    st.warning(f"Không có giao dịch trong khoảng {start_date} — {end_date}.")
    st.stop()

# ── KPI ────────────────────────────────────────────────────────────────────
st.markdown("### 📌 Tóm Tắt")
k1, k2, k3, k4 = st.columns(4)
k1.metric("💰 Tổng Doanh Thu", format_currency(df["total_amount"].sum()))
k2.metric("🧾 Số Giao Dịch", format_number(len(df)))
k3.metric("📊 Giá Trị TB", format_currency(df["total_amount"].mean()))
k4.metric("🖥️ Số Máy HĐ", df["device_id"].nunique() if "device_id" in df.columns else "—")

st.markdown("---")

# ── Revenue trend ──────────────────────────────────────────────────────────
left, right = st.columns(2)

with left:
    st.subheader("📈 Xu Hướng Doanh Thu")
    daily = df.groupby("date")["total_amount"].sum().reset_index()
    fig = px.line(daily, x="date", y="total_amount",
                  labels={"date": "Ngày", "total_amount": "Doanh Thu (₫)"},
                  markers=True)
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("🏆 Sản Phẩm Bán Chạy")
    if stats:
        df_stats = pd.DataFrame(list(stats.items()), columns=["Sản phẩm", "Đã bán"])
        df_stats = df_stats.sort_values("Đã bán", ascending=False).head(10)
        fig2 = px.bar(df_stats, x="Đã bán", y="Sản phẩm", orientation="h",
                      color="Đã bán", color_continuous_scale="Blues")
        fig2.update_layout(showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)

# ── Sales by device ────────────────────────────────────────────────────────
if "device_id" in df.columns:
    st.subheader("🖥️ Doanh Thu Theo Máy")
    by_device = df.groupby("device_id")["total_amount"].sum().reset_index()
    col_pie, col_bar = st.columns(2)
    with col_pie:
        fig3 = px.pie(by_device, names="device_id", values="total_amount",
                      title="Tỷ lệ doanh thu theo máy")
        st.plotly_chart(fig3, use_container_width=True)
    with col_bar:
        fig4 = px.bar(by_device, x="device_id", y="total_amount",
                      title="Doanh thu từng máy",
                      labels={"device_id": "Máy", "total_amount": "Doanh Thu (₫)"})
        st.plotly_chart(fig4, use_container_width=True)

# ── Sales by hour ──────────────────────────────────────────────────────────
st.subheader("🕐 Phân Phối Theo Giờ Trong Ngày")
df["hour"] = df["created_at"].dt.hour
hourly = df.groupby("hour")["total_amount"].sum().reset_index()
fig5 = px.bar(hourly, x="hour", y="total_amount",
              labels={"hour": "Giờ", "total_amount": "Doanh Thu (₫)"},
              title="Doanh thu theo khung giờ")
st.plotly_chart(fig5, use_container_width=True)

st.markdown("---")

# ── Transactions detail table ──────────────────────────────────────────────
st.subheader("📋 Chi Tiết Giao Dịch")
show_cols = [c for c in ["transaction_id", "device_id", "user_id", "total_amount", "payment_status", "created_at"] if c in df.columns]
display = df[show_cols].copy().sort_values("created_at", ascending=False)
display["created_at"] = display["created_at"].apply(lambda x: format_datetime(str(x)))
display["total_amount"] = display["total_amount"].apply(format_currency)
st.dataframe(display, use_container_width=True)

# ── Export ─────────────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("📥 Xuất Báo Cáo")
csv_data = df.to_csv(index=False).encode("utf-8")
st.download_button(
    label="⬇️ Tải CSV",
    data=csv_data,
    file_name=f"transactions_{start_date}_{end_date}.csv",
    mime="text/csv",
)
