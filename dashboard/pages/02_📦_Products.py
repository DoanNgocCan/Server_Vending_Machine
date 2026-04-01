"""
Trang 02: Quản Lý Sản Phẩm — CRUD sản phẩm, số lượng và hình ảnh.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
import pandas as pd
import time

from utils.auth import check_authentication
from utils.api_client import (
    get_all_products, create_product, update_product,
    delete_product, get_image_url, upload_image,
    get_devices, update_device_inventory, get_device_inventory,
    remove_device_inventory
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
            time.sleep(1.5)
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
        df_page = df.iloc[start : start + PAGINATION_SIZE].copy()

        st.caption(f"Hiển thị {len(df_page)}/{total} sản phẩm")

        # Thêm cột lợi nhuận từ file Pricing
        if "price" in df_page.columns and "cost_price" in df_page.columns:
            df_page["Lợi Nhuận (₫)"] = df_page["price"] - df_page["cost_price"]
            df_page["Biên Lợi Nhuận (%)"] = (df_page["Lợi Nhuận (₫)"] / df_page["price"].replace(0, float("nan")) * 100).round(1)

        # Hiển thị bảng
        show_cols = [c for c in ["item_name", "price", "cost_price", "Lợi Nhuận (₫)", "Biên Lợi Nhuận (%)", "units_sold"] if c in df_page.columns]
        st.dataframe(
            df_page[show_cols],
            use_container_width=True,
            column_config={
                "item_name": st.column_config.TextColumn("Tên sản phẩm"),
                "price": st.column_config.NumberColumn("Giá bán (₫)", format="%,.0f"),
                "cost_price": st.column_config.NumberColumn("Giá vốn (₫)", format="%,.0f"),
                "Lợi Nhuận (₫)": st.column_config.NumberColumn("Lợi nhuận (₫)", format="%,.0f"),
                "Biên Lợi Nhuận (%)": st.column_config.NumberColumn("Biên LN (%)", format="%.1f%%"),
                "units_sold": st.column_config.NumberColumn("Đã bán"),
            },
        )

# ════════════════════════════════════════════════════════
# TAB 2: THÊM MỚI & GÁN SẢN PHẨM
# ════════════════════════════════════════════════════════
with tab_create:
    st.subheader("➕ Tạo Sản Phẩm Mới (Master Data)")
    
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
                # KIỂM TRA TRÙNG Ô (SLOT CONFLICT) TRƯỚC KHI TẠO
                slot_conflict = False
                conflict_msg = ""
                if initial_stock > 0 and device_ids:
                    devs_to_check = device_ids if target_device == "Tất cả các máy" else [target_device]
                    for dev in devs_to_check:
                        inv_resp = get_device_inventory(dev)
                        if inv_resp.get("success"):
                            for item in inv_resp.get("inventory", []):
                                if item.get("slot_number") == slot_number:
                                    slot_conflict = True
                                    conflict_msg = f"Máy **{dev}** đang chứa sản phẩm **'{item.get('item_name')}'** tại Ô số **{slot_number}**."
                                    break
                        if slot_conflict:
                            break
                
                if slot_conflict:
                    st.error(f"❌ **Lỗi xung đột vị trí:** {conflict_msg} Vui lòng chọn ô khác để tạo!")
                else:
                    with st.spinner("Đang tạo sản phẩm..."):
                        result = create_product(name.strip(), price, cost_price, description)

                    if result.get("success"):
                        success_msgs = [f"✅ Tạo sản phẩm **{name.strip()}** thành công!"]
                        
                        if initial_stock > 0 and device_ids:
                            devs_to_update = device_ids if target_device == "Tất cả các máy" else [target_device]
                            for dev in devs_to_update:
                                stock_res = update_device_inventory(dev, name.strip(), initial_stock, slot_number)
                                if stock_res.get("success"):
                                    success_msgs.append(f"📦 Đã set {initial_stock} sản phẩm cho máy {dev} ở Ô {slot_number}.")
                                else:
                                    st.warning(f"⚠️ Lỗi set tồn kho máy {dev}: {stock_res.get('message')}")
                        
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

    st.markdown("---")
    
    # ----------------------------------------------------------------------
    # TÍNH NĂNG MỚI: GÁN SẢN PHẨM ĐÃ CÓ VÀO MÁY
    # ----------------------------------------------------------------------
    st.subheader("🔗 Gán Sản Phẩm Đã Có Vào Máy")
    st.info("Sử dụng phần này để đưa một sản phẩm đã có trong Master Data (nhưng bị gỡ ra hoặc chưa từng gán) vào một ô trống cụ thể trên máy.")
    
    # Tải lại danh sách sản phẩm để đảm bảo có data mới nhất
    master_resp = get_all_products()
    master_products = master_resp.get("products", []) if master_resp.get("success") else []
    master_product_names = [p["item_name"] for p in master_products]
    
    with st.form("assign_existing_form", clear_on_submit=True):
        col_a1, col_a2 = st.columns(2)
        with col_a1:
            assign_product = st.selectbox("Chọn sản phẩm từ hệ thống *", options=master_product_names if master_product_names else ["Chưa có sản phẩm"])
            assign_device = st.selectbox("Chọn máy cần gán *", options=device_ids if device_ids else ["Chưa có máy"])
        with col_a2:
            assign_slot = st.selectbox("Chọn ô hiển thị (1-10) *", options=list(range(1, 11)), key="assign_slot")
            assign_qty = st.number_input("Số lượng nạp", min_value=1, step=1, value=10, key="assign_qty")
            
        submitted_assign = st.form_submit_button("🔗 Tiến Hành Gán", type="primary")
        
        if submitted_assign:
            if assign_product == "Chưa có sản phẩm" or assign_device == "Chưa có máy":
                st.error("❌ Hệ thống cần có ít nhất 1 sản phẩm và 1 máy để thực hiện gán!")
            else:
                # KIỂM TRA TRÙNG Ô VÀ TRÙNG SẢN PHẨM TRONG MÁY
                has_error = False
                error_msg = ""
                
                inv_resp = get_device_inventory(assign_device)
                if inv_resp.get("success"):
                    for item in inv_resp.get("inventory", []):
                        # Lỗi 1: Ô được chọn đã bị chiếm dụng (bởi bất kỳ sản phẩm nào)
                        if item.get("slot_number") == assign_slot:
                            has_error = True
                            error_msg = f"Ô số **{assign_slot}** trên máy {assign_device} đang chứa sản phẩm **'{item.get('item_name')}'**."
                            break
                        
                        # Lỗi 2: Sản phẩm này đã tồn tại sẵn trong máy (nằm ở một ô khác)
                        if item.get("item_name") == assign_product:
                            has_error = True
                            error_msg = f"Sản phẩm **'{assign_product}'** đã có sẵn trên máy {assign_device} (hiện đang nằm ở Ô số {item.get('slot_number')}). Mỗi máy chỉ chứa 1 vị trí cho mặt hàng này!"
                            break
                
                if has_error:
                    st.error(f"❌ **Không thể gán:** {error_msg} Vui lòng chọn ô/sản phẩm khác.")
                else:
                    with st.spinner(f"Đang gán {assign_product} vào máy {assign_device}..."):
                        # Gọi API update_device_inventory 
                        res_assign = update_device_inventory(assign_device, assign_product, assign_qty, assign_slot)
                        if res_assign.get("success"):
                            st.success(f"✅ Đã gán thành công **{assign_product}** vào Ô {assign_slot} của máy **{assign_device}** với số lượng {assign_qty}!")
                            st.cache_data.clear()
                            time.sleep(1.5)
                            st.rerun() # Refresh lại trang để cập nhật UI ngay lập tức
                        else:
                            st.error(f"❌ Lỗi: {res_assign.get('message')}")

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
                    # KIỂM TRA TRÙNG Ô (SLOT CONFLICT) TRƯỚC KHI LƯU
                    slot_conflict = False
                    conflict_msg = ""
                    if edit_device and edit_device != "Chưa có máy":
                        inv_resp = get_device_inventory(edit_device)
                        if inv_resp.get("success"):
                            for item in inv_resp.get("inventory", []):
                                # Kiểm tra xem ô mới đã có sản phẩm khác đang chiếm dụng chưa (bỏ qua chính nó)
                                if item.get("slot_number") == new_slot and item.get("item_name") != sel:
                                    slot_conflict = True
                                    conflict_msg = f"Sản phẩm **'{item.get('item_name')}'** đang nằm ở Ô số **{new_slot}** trên máy này."
                                    break
                    
                    if slot_conflict:
                        st.error(f"❌ **Lỗi xung đột vị trí:** {conflict_msg} Vui lòng chọn ô khác!")
                    else:
                        with st.spinner("Đang cập nhật..."):
                            # Update thông tin chung (master data)
                            res_info = update_product(
                                old_name=sel,
                                new_name=new_name if new_name != sel else None,
                                price=new_price,
                                cost_price=new_cost,
                                description=new_desc
                            )
                            
                            # Update số lượng VÀ VỊ TRÍ Ô cho máy cụ thể
                            if edit_device and edit_device != "Chưa có máy":
                                target_name = new_name if new_name != sel else sel
                                res_inv = update_device_inventory(edit_device, target_name, new_qty, new_slot)
                                if not res_inv.get("success"):
                                    st.warning(f"⚠️ Cập nhật tồn kho bị lỗi: {res_inv.get('message')}")
                                
                        if res_info.get("success"):
                            st.success("✅ Đã lưu toàn bộ thay đổi thành công!")
                            st.cache_data.clear()
                            time.sleep(1.5)
                            st.rerun()
                        else:
                            st.error(f"❌ {res_info.get('message')}")

            st.markdown("---")
            # --- KHU VỰC GỠ/XÓA SẢN PHẨM ---
            st.subheader("🗑️ Gỡ / Xóa Sản Phẩm Này")
            
            delete_mode = st.radio(
                "Tùy chọn phạm vi xóa:",
                ["Gỡ khỏi MỘT MÁY CỤ THỂ", "Xóa VĨNH VIỄN khỏi toàn hệ thống"]
            )
            
            # TRƯỜNG HỢP 1: XÓA Ở 1 MÁY
            if delete_mode == "Gỡ khỏi MỘT MÁY CỤ THỂ":
                st.info("💡 Sản phẩm sẽ biến mất khỏi ô trên máy được chọn, nhưng vẫn còn trong Master Data để gán lại sau.")
                del_device = st.selectbox("Chọn máy để gỡ:", device_ids if device_ids else ["Chưa có máy"], key="del_dev_select")
                
                if st.button(f"🗑️ Xác nhận gỡ khỏi {del_device}", type="primary"):
                    with st.spinner(f"Đang gỡ khỏi {del_device}..."):
                        result = remove_device_inventory(del_device, sel)
                        if result.get("success"):
                            st.success(f"✅ Đã gỡ thành công {sel} khỏi {del_device}")
                            st.cache_data.clear()
                            time.sleep(1.5)
                            st.rerun()
                        else:
                            st.error(f"❌ Lỗi: {result.get('message')}")

            # TRƯỜNG HỢP 2: XÓA TOÀN HỆ THỐNG
            elif delete_mode == "Xóa VĨNH VIỄN khỏi toàn hệ thống":
                st.warning("⚠️ **Nguy hiểm:** Xóa khỏi Master Data và tất cả các máy. Hành động này không thể hoàn tác.")
                
                if st.button("🗑️ Xác nhận xóa vĩnh viễn", type="primary"):
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
                                time.sleep(1.5)
                                st.rerun()
                            else:
                                st.error(f"❌ Lỗi: {result.get('message')}")
                    with c2:
                        if st.button("❌ Hủy bỏ"):
                            st.session_state.pop("confirm_delete_btn", None)
                            time.sleep(1.5)
                            st.rerun()