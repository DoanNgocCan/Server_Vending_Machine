"""
Trang 02: Quản Lý Sản Phẩm — CRUD sản phẩm, số lượng và hình ảnh.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
import pandas as pd

from utils.auth import check_authentication
from utils.api_client import (
    get_all_products, create_product, update_product,
    delete_product, get_image_url, upload_image,
    get_devices, update_device_inventory, get_device_inventory
)
from utils.helpers import format_currency, format_datetime, validate_image_file
from config import PAGINATION_SIZE

st.set_page_config(page_title="Sản Phẩm — Vending Admin", page_icon="📦", layout="wide")

if not check_authentication():
    st.stop()

st.title("📦 Quản Lý Sản Phẩm")

# Tải danh sách máy (devices) để gán tồn kho
devices_resp = get_devices()
devices = devices_resp.get("devices", []) if devices_resp.get("success") else []
device_ids = [d["device_id"] for d in devices]

tab_list, tab_create, tab_edit = st.tabs(["📋 Danh Sách", "➕ Thêm Mới", "✏️ Chỉnh Sửa & Xóa"])

# ════════════════════════════════════════════════════════
# TAB 1: DANH SÁCH SẢN PHẨM
# ════════════════════════════════════════════════════════
with tab_list:
    col_reload, col_search = st.columns([1, 3])
    with col_reload:
        if st.button("🔄 Làm mới dữ liệu"):
            st.cache_data.clear()
            st.rerun()
    with col_search:
        search_q = st.text_input("🔍 Tìm kiếm sản phẩm", placeholder="Nhập tên sản phẩm...")

    with st.spinner("Đang tải danh sách sản phẩm..."):
        resp = get_all_products()

    if not resp.get("success"):
        st.error(f"❌ Lỗi: {resp.get('message', 'Không thể kết nối server')}")
        st.stop()

    products = resp.get("products", [])
    if not products:
        st.info("Chưa có sản phẩm nào trong hệ thống. Hãy thêm sản phẩm mới ở tab bên cạnh!")
    else:
        df = pd.DataFrame(products)

        # Lọc theo tìm kiếm
        if search_q:
            df = df[df["item_name"].str.contains(search_q, case=False, na=False)]

        # Phân trang
        total = len(df)
        page_count = max(1, (total - 1) // PAGINATION_SIZE + 1)
        page = st.number_input("Trang", min_value=1, max_value=page_count, value=1, step=1)
        start = (page - 1) * PAGINATION_SIZE
        df_page = df.iloc[start : start + PAGINATION_SIZE]

        st.caption(f"Hiển thị {len(df_page)}/{total} sản phẩm")

        # Hiển thị bảng
        show_cols = [c for c in ["item_name", "price", "cost_price", "description", "units_sold"] if c in df_page.columns]
        st.dataframe(
            df_page[show_cols],
            use_container_width=True,
            column_config={
                "item_name": st.column_config.TextColumn("Tên sản phẩm"),
                "price": st.column_config.NumberColumn("Giá bán (₫)", format="%,.0f"),
                "cost_price": st.column_config.NumberColumn("Giá vốn (₫)", format="%,.0f"),
                "units_sold": st.column_config.NumberColumn("Đã bán"),
                "description": st.column_config.TextColumn("Mô tả"),
            },
        )

# ════════════════════════════════════════════════════════
# TAB 2: THÊM SẢN PHẨM MỚI (Kèm số lượng)
# ════════════════════════════════════════════════════════
with tab_create:
    st.subheader("➕ Thêm Sản Phẩm Mới")
    
    with st.form("create_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Tên sản phẩm *", placeholder="VD: Coca Cola 330ml")
            price = st.number_input("Giá bán (₫) *", min_value=0.0, step=1000.0)
            cost_price = st.number_input("Giá vốn (₫)", min_value=0.0, step=1000.0)
            
        with col2:
            initial_stock = st.number_input("Số lượng tồn kho ban đầu", min_value=0, step=1, value=10)
            slot_number = st.selectbox("Chọn ô hiển thị trên máy (1-10) *", options=list(range(1, 11)))
            target_device = st.selectbox(
                "Áp dụng số lượng cho máy:", 
                ["Tất cả các máy"] + device_ids if device_ids else ["Chưa có máy nào"]
            )
            image_file = st.file_uploader("Ảnh sản phẩm (jpg, png, webp, tối đa 5MB)", type=["jpg", "jpeg", "png", "webp"])

        description = st.text_area("Mô tả thêm", placeholder="Mô tả sản phẩm...")
        submitted = st.form_submit_button("➕ Tạo Sản Phẩm", type="primary")

        if submitted:
            if not name.strip():
                st.error("❌ Vui lòng nhập tên sản phẩm!")
            elif price <= 0:
                st.error("❌ Giá bán phải lớn hơn 0!")
            else:
                with st.spinner("Đang tạo sản phẩm..."):
                    result = create_product(name.strip(), price, cost_price, description)

                if result.get("success"):
                    success_msgs = [f"✅ Tạo sản phẩm **{name.strip()}** thành công!"]
                    
                    # Cập nhật số lượng
                    if initial_stock > 0 and device_ids:
                        devs_to_update = device_ids if target_device == "Tất cả các máy" else [target_device]
                        for dev in devs_to_update:
                            # Chú ý: Cần truyền thêm tham số slot_number vào hàm này
                            stock_res = update_device_inventory(dev, name.strip(), initial_stock, slot_number)
                            if stock_res.get("success"):
                                success_msgs.append(f"📦 Đã set {initial_stock} sản phẩm cho máy {dev}.")
                            else:
                                st.warning(f"⚠️ Lỗi set tồn kho máy {dev}: {stock_res.get('message')}")
                    
                    # Upload ảnh
                    if image_file:
                        valid, err = validate_image_file(image_file)
                        if valid:
                            img_result = upload_image(name.strip(), image_file.getvalue(), image_file.name)
                            if img_result.get("success"):
                                success_msgs.append("📸 Upload ảnh thành công!")
                            else:
                                st.warning(f"⚠️ Upload ảnh lỗi: {img_result.get('message')}")
                        else:
                            st.warning(f"⚠️ Ảnh không hợp lệ: {err}")
                    
                    for msg in success_msgs:
                        st.success(msg)
                    st.cache_data.clear()
                else:
                    st.error(f"❌ {result.get('message', 'Tạo thất bại')}")

# ════════════════════════════════════════════════════════
# TAB 3: CHỈNH SỬA, SET SỐ LƯỢNG & XÓA SẢN PHẨM
# ════════════════════════════════════════════════════════
with tab_edit:
    st.subheader("✏️ Chỉnh Sửa & Xóa Sản Phẩm")

    resp2 = get_all_products()
    products2 = resp2.get("products", []) if resp2.get("success") else []
    
    if not products2:
        st.info("Chưa có sản phẩm nào để chỉnh sửa.")
    else:
        df2 = pd.DataFrame(products2)
        product_names2 = df2["item_name"].tolist()
        
        col_select, col_img = st.columns([2, 1])
        with col_select:
            sel = st.selectbox("Chọn sản phẩm cần thao tác:", product_names2, key="edit_select")
        
        if sel:
            cur = df2[df2["item_name"] == sel].iloc[0]

            with col_img:
                if cur.get("image_url"):
                    img_url = get_image_url(cur["image_url"])
                    if img_url:
                        st.image(img_url, width=120, caption="Ảnh hiện tại")

            st.markdown("---")
            
            # --- FORM CHỈNH SỬA THÔNG TIN & SỐ LƯỢNG ---
            with st.form("edit_form"):
                st.markdown("**1. Cập nhật Thông Tin Chung**")
                col_e1, col_e2 = st.columns(2)
                with col_e1:
                    new_name = st.text_input("Tên sản phẩm", value=sel)
                    new_price = st.number_input("Giá bán mới (₫)", value=float(cur.get("price", 0)), step=1000.0)
                with col_e2:
                    new_cost = st.number_input("Giá vốn mới (₫)", value=float(cur.get("cost_price", 0)), step=1000.0)
                    new_desc = st.text_area("Mô tả", value=cur.get("description", "") or "", height=68)

                st.markdown("**2. Điều chỉnh Số Lượng & Vị Trí Ô (Slot)**")
                col_s1, col_s2, col_s3 = st.columns(3) # Chia làm 3 cột
                with col_s1:
                    edit_device = st.selectbox("Chọn máy cần đổi:", device_ids if device_ids else ["Chưa có máy"], key="edit_dev")
                
                # Tìm số lượng và số ô hiện tại của sản phẩm trên máy này
                current_qty = 0
                current_slot = 1
                if edit_device and edit_device != "Chưa có máy":
                    inv_r = get_device_inventory(edit_device)
                    if inv_r.get("success"):
                        for item in inv_r.get("inventory", []):
                            if item.get("item_name") == sel:
                                current_qty = item.get("units_left", 0)
                                current_slot = item.get("slot_number") or 1
                                break
                                
                with col_s2:
                    new_qty = st.number_input(f"Số lượng (hiện tại: {current_qty})", min_value=0, step=1, value=current_qty)
                with col_s3:
                    # Cho phép admin đổi ô
                    new_slot = st.selectbox(f"Số ô (hiện tại: {current_slot})", options=list(range(1, 11)), index=current_slot-1)

                save = st.form_submit_button("💾 Lưu Toàn Bộ Thay Đổi", type="primary")
                if save:
                    with st.spinner("Đang cập nhật..."):
                        # Update thông tin chung (master data)
                        res_info = update_product(
                            old_name=sel,
                            new_name=new_name if new_name != sel else None,
                            price=new_price,
                        )
                        
                        # Update số lượng VÀ VỊ TRÍ Ô cho máy cụ thể
                        if edit_device and edit_device != "Chưa có máy":
                            target_name = new_name if new_name != sel else sel
                            # Truyền đủ 4 tham số: device_id, item_name, qty, slot_number
                            update_device_inventory(edit_device, target_name, new_qty, new_slot)
                            
                    if res_info.get("success"):
                        st.success("✅ Đã lưu toàn bộ thay đổi thành công!")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error(f"❌ {res_info.get('message')}")

            st.markdown("---")
            # --- KHU VỰC XÓA SẢN PHẨM ---
            st.subheader("🗑️ Xóa Sản Phẩm Này")
            st.warning("⚠️ **Nguy hiểm:** Việc xóa sản phẩm sẽ xóa sản phẩm này khỏi Master Data và tất cả các máy. Hành động này không thể hoàn tác.")
            
            if st.button("🗑️ Xác nhận xóa sản phẩm", type="primary", use_container_width=True):
                st.session_state["confirm_delete_btn"] = sel
                
            if st.session_state.get("confirm_delete_btn") == sel:
                st.error(f"Bạn có chắc chắn muốn xóa vĩnh viễn **{sel}**?")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("✅ Vâng, Xóa ngay!"):
                        result = delete_product(sel)
                        if result.get("success"):
                            st.success(f"✅ Đã xóa thành công: {sel}")
                            st.session_state.pop("confirm_delete_btn", None)
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.error(f"❌ Lỗi: {result.get('message')}")
                with c2:
                    if st.button("❌ Hủy bỏ"):
                        st.session_state.pop("confirm_delete_btn", None)
                        st.rerun()