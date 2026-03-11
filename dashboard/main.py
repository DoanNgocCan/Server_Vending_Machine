# dashboard/pages/home_dashboard.py
import streamlit as st
import plotly.express as px
from utils import load_data, format_number
from datetime import datetime

st.set_page_config(page_title="Vending Machine Analytics", layout="wide")

st.title("📊 Vending Machine Dashboard")
st.markdown(f"Dữ liệu cập nhật lúc: {datetime.now().strftime('%H:%M %d/%m/%Y')}")

if st.button('🔄 Cập nhật dữ liệu mới nhất'):
    # Lệnh này sẽ xóa sạch bộ nhớ đệm
    st.cache_data.clear()
    # Chạy lại trang
    st.rerun()

# --- LOAD DATA ---
with st.spinner("Đang đồng bộ dữ liệu từ Server..."):
    data_pack = load_data()
    df = data_pack.get('df_transactions')
    count_products = data_pack.get('total_products')
    count_customers = data_pack.get('total_customers')

if df.empty:
    st.warning("Chưa có giao dịch nào được ghi nhận!")
    st.stop()

# --- KPI SECTION ---
col1, col2, col3, col4 = st.columns(4)

with col1:
    total_sales = df['TotalPrice'].sum()
    st.metric("💰 Doanh Thu Tổng", f"{format_number(total_sales)} VNĐ")

with col2:
    st.metric("👥 Khách Hàng Đã Đăng Ký", format_number(count_customers))
    
with col3:
    st.metric("📦 Sản Phẩm Đang Bán", format_number(count_products))
    
with col4:
    total_transactions = df['InvoiceNo'].nunique()
    st.metric("🧾 Số Đơn Hàng", format_number(total_transactions))

st.markdown("---")

# --- CHART SECTION ---
st.subheader("📈 Xu Hướng Doanh Thu")

# Gom nhóm theo Năm-Tháng
monthly_sales = df.groupby([df['Year'], df['Month']])['TotalPrice'].sum().reset_index()
monthly_sales['YearMonth'] = monthly_sales['Year'].astype(str) + '-' + monthly_sales['Month'].astype(str).str.zfill(2)

# Vẽ biểu đồ
fig = px.line(
    monthly_sales, 
    x='YearMonth', 
    y='TotalPrice',
    title='Biểu đồ Doanh thu theo Tháng',
    labels={'YearMonth': 'Tháng', 'TotalPrice': 'Doanh thu (VNĐ)'},
    markers=True
)
fig.update_layout(xaxis_tickangle=-45)
st.plotly_chart(fig, use_container_width=True)

# --- CHI TIẾT GIAO DỊCH GẦN ĐÂY ---
st.subheader("📋 Giao Dịch Mới Nhất")
# Hiển thị bảng nhưng bỏ bớt cột rác (JSON items dài dòng)
display_df = df[['InvoiceNo', 'InvoiceDate', 'TotalPrice', 'payment_status', 'CustomerID']].copy()
display_df = display_df.sort_values(by='InvoiceDate', ascending=False).head(10)
st.dataframe(display_df, use_container_width=True)