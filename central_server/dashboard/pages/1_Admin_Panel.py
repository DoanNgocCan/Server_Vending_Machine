# dashboard/pages/1_Admin_Panel.py
import streamlit as st
import pandas as pd
import sys
import os
# Hack path để import services từ thư mục cha
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from services import fetch_products, update_product_info

st.set_page_config(page_title="Admin Panel", layout="wide")
st.title("🛠️ Quản Trị Sản Phẩm & Kho")

# 1. Chọn máy để làm việc (Vì kho là riêng từng máy)
# Ở đây tôi hardcode list máy, thực tế bạn có thể gọi API lấy list device
device_list = ["VENDING_MACHINE_01", "ESP32_SIMULATOR_01", "ESP32_SIMULATOR_02"]
selected_device = st.selectbox("Chọn máy bán hàng:", device_list)

if st.button("🔄 Làm mới dữ liệu"):
    st.cache_data.clear()
    st.rerun()

# 2. Tải dữ liệu sản phẩm của máy đã chọn
with st.spinner("Đang tải dữ liệu..."):
    # Hàm này sẽ lấy giá Master và Tồn kho riêng của selected_device
    products = fetch_products(device_id=selected_device)

if not products:
    st.warning("Không tải được danh sách sản phẩm.")
    st.stop()

df = pd.DataFrame(products)

# 3. Hiển thị bảng tổng quan
st.subheader(f"Kho hàng hiện tại: {selected_device}")
# Hiển thị các cột quan trọng
st.dataframe(
    df[['item_name', 'price', 'units_left', 'description']], 
    use_container_width=True,
    column_config={
        "price": st.column_config.NumberColumn("Giá bán (VNĐ)", format="%d đ"),
        "units_left": st.column_config.NumberColumn("Tồn kho (Cái)"),
    }
)

st.markdown("---")

# 4. Form Cập nhật Sản phẩm
st.subheader("✏️ Chỉnh sửa sản phẩm")

col1, col2 = st.columns(2)

with col1:
    # Chọn sản phẩm để sửa
    product_names = df['item_name'].tolist()
    selected_product_name = st.selectbox("Chọn sản phẩm cần sửa:", product_names)
    
    # Lấy thông tin hiện tại của sản phẩm đã chọn
    current_info = df[df['item_name'] == selected_product_name].iloc[0]
    
    st.info(f"Đang sửa: **{selected_product_name}**")
    
    # Form nhập liệu
    with st.form("update_form"):
        # Đổi tên (Cảnh báo người dùng)
        new_name = st.text_input("Tên sản phẩm (Sửa nếu muốn đổi tên):", value=selected_product_name)
        if new_name != selected_product_name:
            st.warning("⚠️ Lưu ý: Đổi tên sẽ cập nhật trên toàn hệ thống (tất cả các máy).")
            
        # Đổi giá
        new_price = st.number_input("Giá bán mới (VNĐ):", value=float(current_info['price']), step=1000.0)
        
        # Nhập kho thêm
        add_stock = st.number_input(f"Nhập thêm hàng vào máy {selected_device}:", value=0, step=1)
        
        submitted = st.form_submit_button("Lưu Thay Đổi")
        
        if submitted:
            success, msg = update_product_info(
                old_name=selected_product_name,
                new_name=new_name,
                price=new_price,
                add_stock=add_stock,
                device_id=selected_device
            )
            
            if success:
                st.success(f"✅ {msg}")
                # Xóa cache để cập nhật lại bảng
                st.cache_data.clear()
                # Đợi 1s rồi reload
                import time
                time.sleep(1)
                st.rerun()
            else:
                st.error(f"❌ Lỗi: {msg}")