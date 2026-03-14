"""
Trang 02: Quản Lý Sản Phẩm — CRUD sản phẩm.
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
)
from utils.helpers import format_currency, format_datetime, validate_image_file
from config import PAGINATION_SIZE

st.set_page_config(page_title="Sản Phẩm — Vending Admin", page_icon="📦", layout="wide")

if not check_authentication():
    st.stop()

st.title("📦 Quản Lý Sản Phẩm")

tab_list, tab_create, tab_edit = st.tabs(["📋 Danh Sách", "➕ Thêm Mới", "✏️ Chỉnh Sửa"])

# ════════════════════════════════════════════════════════
# TAB 1: DANH SÁCH SẢN PHẨM
# ════════════════════════════════════════════════════════
with tab_list:
    col_reload, col_search = st.columns([1, 3])
    with col_reload:
        if st.button("🔄 Làm mới"):
            st.cache_data.clear()
            st.rerun()
    with col_search:
        search_q = st.text_input("🔍 Tìm kiếm sản phẩm", placeholder="Nhập tên...")

    with st.spinner("Đang tải..."):
        resp = get_all_products()

    if not resp.get("success"):
        st.error(f"❌ Lỗi: {resp.get('message', 'Không thể kết nối server')}")
        st.stop()

    products = resp.get("products", [])
    if not products:
        st.info("Chưa có sản phẩm nào. Hãy thêm sản phẩm mới!")
    else:
        df = pd.DataFrame(products)

        # Filter
        if search_q:
            df = df[df["item_name"].str.contains(search_q, case=False, na=False)]

        # Pagination
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

        # ── Xóa sản phẩm ──────────────────────────────────
        st.markdown("---")
        st.subheader("🗑️ Xóa Sản Phẩm")
        product_names = df["item_name"].tolist()
        del_name = st.selectbox("Chọn sản phẩm cần xóa:", product_names, key="del_select")
        if st.button("🗑️ Xóa sản phẩm này", type="secondary"):
            st.session_state["confirm_delete"] = del_name

        if st.session_state.get("confirm_delete"):
            st.warning(f"⚠️ Bạn chắc chắn muốn xóa **{st.session_state['confirm_delete']}**?")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ Xác nhận xóa", type="primary"):
                    result = delete_product(st.session_state["confirm_delete"])
                    if result.get("success"):
                        st.success(f"✅ Đã xóa: {st.session_state['confirm_delete']}")
                        st.session_state.pop("confirm_delete", None)
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error(f"❌ {result.get('message')}")
            with c2:
                if st.button("❌ Hủy"):
                    st.session_state.pop("confirm_delete", None)
                    st.rerun()

# ════════════════════════════════════════════════════════
# TAB 2: THÊM SẢN PHẨM MỚI
# ════════════════════════════════════════════════════════
with tab_create:
    st.subheader("➕ Thêm Sản Phẩm Mới")
    with st.form("create_form", clear_on_submit=True):
        name = st.text_input("Tên sản phẩm *", placeholder="VD: Coca Cola 330ml")
        price = st.number_input("Giá bán (₫) *", min_value=0.0, step=1000.0)
        cost_price = st.number_input("Giá vốn (₫)", min_value=0.0, step=1000.0)
        description = st.text_area("Mô tả", placeholder="Mô tả sản phẩm...")
        image_file = st.file_uploader("Ảnh sản phẩm (jpg, png, webp, tối đa 5MB)", type=["jpg", "jpeg", "png", "webp"])
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
                    # Upload ảnh nếu có
                    if image_file:
                        valid, err = validate_image_file(image_file)
                        if valid:
                            img_result = upload_image(name.strip(), image_file.getvalue(), image_file.name)
                            if img_result.get("success"):
                                st.success(f"✅ Đã tạo sản phẩm và upload ảnh thành công!")
                            else:
                                st.warning(f"⚠️ Tạo sản phẩm OK nhưng upload ảnh lỗi: {img_result.get('message')}")
                        else:
                            st.warning(f"⚠️ Tạo sản phẩm OK nhưng ảnh không hợp lệ: {err}")
                    else:
                        st.success(f"✅ {result.get('message', 'Tạo sản phẩm thành công!')}")
                    st.cache_data.clear()
                else:
                    st.error(f"❌ {result.get('message', 'Tạo thất bại')}")

# ════════════════════════════════════════════════════════
# TAB 3: CHỈNH SỬA SẢN PHẨM
# ════════════════════════════════════════════════════════
with tab_edit:
    st.subheader("✏️ Chỉnh Sửa Thông Tin Sản Phẩm")

    resp2 = get_all_products()
    products2 = resp2.get("products", []) if resp2.get("success") else []
    if not products2:
        st.info("Chưa có sản phẩm nào.")
    else:
        df2 = pd.DataFrame(products2)
        product_names2 = df2["item_name"].tolist()
        sel = st.selectbox("Chọn sản phẩm cần sửa:", product_names2, key="edit_select")

        if sel:
            cur = df2[df2["item_name"] == sel].iloc[0]

            # Hiển thị ảnh hiện tại
            if cur.get("image_url"):
                img_url = get_image_url(cur["image_url"])
                if img_url:
                    st.image(img_url, width=150, caption="Ảnh hiện tại")

            with st.form("edit_form"):
                new_name = st.text_input("Tên sản phẩm", value=sel)
                if new_name != sel:
                    st.warning("⚠️ Đổi tên sẽ cập nhật trên toàn hệ thống!")
                new_price = st.number_input("Giá bán mới (₫)", value=float(cur.get("price", 0)), step=1000.0)
                new_cost = st.number_input("Giá vốn mới (₫)", value=float(cur.get("cost_price", 0)), step=1000.0)
                new_desc = st.text_area("Mô tả", value=cur.get("description", "") or "")

                save = st.form_submit_button("💾 Lưu Thay Đổi", type="primary")
                if save:
                    with st.spinner("Đang cập nhật..."):
                        result = update_product(
                            old_name=sel,
                            new_name=new_name if new_name != sel else None,
                            price=new_price,
                        )
                    if result.get("success"):
                        st.success("✅ Cập nhật thành công!")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error(f"❌ {result.get('message')}")
