"""
Trang 01: Dashboard Overview — Tổng quan hệ thống.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date, timedelta

from utils.auth import check_authentication
from utils.api_client import get_all_products, get_devices, get_transactions, get_inventory_stats, get_device_inventory, get_advanced_analytics
from utils.helpers import format_currency, format_number, format_datetime, stock_status_color

st.set_page_config(page_title="Dashboard — Vending Admin", page_icon="📊", layout="wide")

if not check_authentication():
    st.stop()

st.title("📊 Dashboard Phân Tích & Tổng Quan")
st.caption(f"Cập nhật lúc: {datetime.now().strftime('%H:%M %d/%m/%Y')}")

# Tích hợp bộ lọc ngày từ Analytics
col_date1, col_date2, col_reload = st.columns([2, 2, 1])
with col_date1:
    start_date = st.date_input("Từ ngày:", value=date.today() - timedelta(days=30))
with col_date2:
    end_date = st.date_input("Đến ngày:", value=date.today())
with col_reload:
    st.write("")
    if st.button("🔄 Làm mới dữ liệu"):
        st.cache_data.clear()
        st.rerun()

# ── Fetch data ─────────────────────────────────────────────────────────────
with st.spinner("Đang tải dữ liệu và phân tích..."):
    products_resp = get_all_products()
    devices_resp = get_devices()
    trans_resp = get_transactions(limit=5000) 
    analytics_resp = get_advanced_analytics() # Gọi API phân tích nâng cao mới thêm

products = products_resp.get("products", []) if products_resp.get("success") else []
devices = devices_resp.get("devices", []) if devices_resp.get("success") else []
transactions = trans_resp.get("transactions", []) if trans_resp.get("success") else []
analytics_data = analytics_resp.get("data", {}) if analytics_resp and analytics_resp.get("success") else {}

df_trans = pd.DataFrame(transactions) if transactions else pd.DataFrame()

# Lọc giao dịch theo ngày cho Line Chart
if not df_trans.empty and "created_at" in df_trans.columns:
    df_trans["created_at"] = pd.to_datetime(df_trans["created_at"])
    df_trans["date"] = df_trans["created_at"].dt.date
    df_trans = df_trans[(df_trans["date"] >= start_date) & (df_trans["date"] <= end_date)]

# ── KPI Cards ──────────────────────────────────────────────────────────────
st.markdown("### 📌 Chỉ Số Tổng Quan Toàn Hệ Thống")
k1, k2, k3, k4 = st.columns(4)

# Lấy tổng doanh thu từ API Advanced Analytics nếu có, ngược lại tính từ df_trans
total_revenue_overall = analytics_data.get('total_revenue', 0) if analytics_data else (df_trans["total_amount"].sum() if not df_trans.empty else 0)

k1.metric("💰 Tổng Doanh Thu", format_currency(total_revenue_overall))
k2.metric("📦 Mặt Hàng", len(products))
k3.metric("🖥️ Máy Kết Nối", len(devices))
k4.metric("🧾 Tổng Giao Dịch (Kỳ này)", format_number(len(df_trans)))

st.markdown("---")

# ── Phân Tích Chuyên Sâu (Charts) ─────────────────────────────────────────
st.markdown("### 🔍 Phân Tích Chuyên Sâu")
col1, col2 = st.columns(2)

with col1:
    st.subheader("📈 Doanh Thu Theo Ngày")
    if not df_trans.empty:
        daily = df_trans.groupby("date")["total_amount"].sum().reset_index()
        fig = px.line(daily, x="date", y="total_amount",
                      labels={"date": "Ngày", "total_amount": "Doanh Thu (₫)"},
                      markers=True)
        fig.update_layout(margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Chưa có dữ liệu giao dịch trong khoảng thời gian này.")

    st.subheader("📍 Doanh Thu Theo Từng Máy")
    rev_device = analytics_data.get('revenue_by_device', [])
    if rev_device:
        df_rev = pd.DataFrame(rev_device)
        fig_rev = px.bar(df_rev, x="device_id", y="revenue", 
                         labels={"device_id": "Mã Máy", "revenue": "Doanh Thu (₫)"},
                         color="revenue", color_continuous_scale="Blues")
        fig_rev.update_layout(margin=dict(l=0, r=0, t=30, b=0), showlegend=False)
        st.plotly_chart(fig_rev, use_container_width=True)
    else:
        st.info("Chưa có dữ liệu doanh thu theo máy.")

with col2:
    st.subheader("🏆 Top 5 Sản Phẩm Bán Chạy Nhất")
    top_prods = analytics_data.get('top_products', [])
    if top_prods:
        df_top = pd.DataFrame(top_prods)
        fig2 = px.bar(df_top.sort_values("units_sold", ascending=True), 
                      x="units_sold", y="item_name", orientation="h",
                      labels={"units_sold": "Số lượng đã bán", "item_name": "Sản phẩm"},
                      color="units_sold", color_continuous_scale="Reds")
        fig2.update_layout(margin=dict(l=0, r=0, t=30, b=0), showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Chưa có dữ liệu thống kê sản phẩm.")
        
    st.subheader("🗑️ Sản Phẩm Cần Tối Ưu (Ế ẩm)")
    st.caption("Các mặt hàng bán được rất ít (<= 3 sản phẩm) tại từng vị trí máy. Khuyến nghị cân nhắc thay thế.")
    underperforming = analytics_data.get('underperforming_products', [])
    if underperforming:
        df_under = pd.DataFrame(underperforming)
        df_under.rename(columns={
            'device_id': 'Mã Máy',
            'item_name': 'Tên Sản Phẩm',
            'units_sold': 'Đã Bán'
        }, inplace=True)
        st.dataframe(df_under, use_container_width=True, hide_index=True)
    else:
        st.success("Tốt! Không có sản phẩm nào bán quá chậm (< 3 cái).")
st.markdown("---")
st.subheader("🎯 Top Sản Phẩm Bán Chạy Theo Từng Máy")

# Lấy dữ liệu từ object analytics_data đã fetch ở trên
top_by_device = analytics_data.get('top_products_by_device', [])

if top_by_device:
    df_top_dev = pd.DataFrame(top_by_device)
    
    if {'device_id', 'item_name', 'units_sold'}.issubset(df_top_dev.columns):
        device_list = df_top_dev['device_id'].unique()
        
        # Tạo tab cho từng máy
        tabs = st.tabs([f"📱 Máy {d}" for d in device_list])
        
        for i, dev_id in enumerate(device_list):
            with tabs[i]:
                # Lọc data theo mã máy và sắp xếp để vẽ biểu đồ ngang
                df_filtered = df_top_dev[df_top_dev['device_id'] == dev_id].sort_values("units_sold", ascending=True)
                
                if not df_filtered.empty:
                    fig_dev = px.bar(
                        df_filtered, 
                        x="units_sold", 
                        y="item_name", 
                        orientation="h",
                        labels={"units_sold": "Số lượng đã bán", "item_name": "Sản phẩm"},
                        color="units_sold", 
                        color_continuous_scale="Greens",
                        text="units_sold" # Hiển thị số ngay trên cột
                    )
                    fig_dev.update_layout(margin=dict(l=0, r=0, t=30, b=0), showlegend=False)
                    st.plotly_chart(fig_dev, use_container_width=True)
                else:
                    st.info(f"Chưa có dữ liệu bán hàng cho máy {dev_id}.")
    else:
        st.warning("Dữ liệu trả về thiếu các cột chuẩn: 'device_id', 'item_name', 'units_sold'.")
else:
    st.info("💡 Chưa có dữ liệu hoặc API backend chưa trả về key 'top_products_by_device'.")

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

# ── Recent Transactions & Export ────────────────────────────────────────────
st.subheader("📋 Giao Dịch Gần Nhất")
if not df_trans.empty:
    cols_show = [c for c in ["transaction_id", "device_id", "total_amount", "payment_status", "created_at"] if c in df_trans.columns]
    display = df_trans[cols_show].sort_values("created_at", ascending=False).head(50).copy()
    
    # Nút Export CSV
    csv_data = df_trans.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Tải File Báo Cáo CSV", data=csv_data, file_name=f"transactions_{start_date}_{end_date}.csv", mime="text/csv")
    
    if "total_amount" in display.columns:
        display["total_amount"] = display["total_amount"].apply(format_currency)
    if "created_at" in display.columns:
        display["created_at"] = display["created_at"].apply(format_datetime)
    st.dataframe(display, use_container_width=True)
else:
    st.info("Chưa có giao dịch nào.")