"""
Trang 05: Quản Lý Ảnh — Upload & quản lý ảnh sản phẩm.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
import pandas as pd
import requests

from utils.auth import check_authentication
from utils.api_client import get_all_products, upload_image, get_image_url
from utils.helpers import validate_image_file

st.set_page_config(page_title="Ảnh Sản Phẩm — Vending Admin", page_icon="📸", layout="wide")

if not check_authentication():
    st.stop()

st.title("📸 Quản Lý Ảnh Sản Phẩm")

if st.button("🔄 Làm mới"):
    st.cache_data.clear()
    st.rerun()

with st.spinner("Đang tải danh sách sản phẩm..."):
    resp = get_all_products()

products = resp.get("products", []) if resp.get("success") else []
if not products:
    st.warning("Chưa có sản phẩm nào.")
    st.stop()

product_names = [p["item_name"] for p in products]
product_map = {p["item_name"]: p for p in products}

tab_single, tab_bulk, tab_gallery = st.tabs(["📤 Upload Đơn Lẻ", "📦 Upload Hàng Loạt", "🖼️ Thư Viện Ảnh"])

# ════════════════════════════════════════════════════════
# TAB 1: UPLOAD ĐƠN LẺ
# ════════════════════════════════════════════════════════
with tab_single:
    st.subheader("📤 Upload Ảnh Cho Một Sản Phẩm")

    sel_prod = st.selectbox("Chọn sản phẩm:", product_names, key="single_prod")

    if sel_prod:
        prod_info = product_map.get(sel_prod, {})
        existing_url = get_image_url(prod_info.get("image_url"))
        if existing_url:
            st.image(existing_url, width=200, caption="Ảnh hiện tại")
        else:
            st.info("Sản phẩm này chưa có ảnh.")

    uploaded = st.file_uploader(
        "Chọn ảnh mới (JPG, PNG, WebP — tối đa 5MB)",
        type=["jpg", "jpeg", "png", "webp"],
        key="single_upload",
    )

    if uploaded:
        st.image(uploaded, width=200, caption="Xem trước ảnh mới")
        valid, err = validate_image_file(uploaded)
        if not valid:
            st.error(f"❌ {err}")
        else:
            if st.button("⬆️ Upload Ảnh Này", type="primary"):
                with st.spinner("Đang upload..."):
                    result = upload_image(sel_prod, uploaded.getvalue(), uploaded.name)
                if result.get("success"):
                    st.success(f"✅ Upload thành công! Ảnh URL: `{result.get('image_url')}`")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error(f"❌ {result.get('message')}")

# ════════════════════════════════════════════════════════
# TAB 2: UPLOAD HÀNG LOẠT
# ════════════════════════════════════════════════════════
with tab_bulk:
    st.subheader("📦 Upload Ảnh Hàng Loạt")
    st.info(
        "💡 **Cách dùng**: Đặt tên file ảnh trùng với tên sản phẩm (không phân biệt chữ hoa/thường). "
        "VD: `Coca Cola 330ml.jpg`"
    )

    bulk_files = st.file_uploader(
        "Kéo thả nhiều ảnh cùng lúc",
        type=["jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True,
        key="bulk_upload",
    )

    if bulk_files:
        st.markdown(f"**Đã chọn {len(bulk_files)} file:**")

        # Preview & match
        rows = []
        for f in bulk_files:
            base = os.path.splitext(f.name)[0]
            matched = next((p for p in product_names if p.lower() == base.lower()), None)
            valid, err = validate_image_file(f)
            rows.append({
                "File": f.name,
                "Sản phẩm khớp": matched or "❌ Không tìm thấy",
                "Hợp lệ": "✅" if valid else f"❌ {err}",
                "_file": f,
                "_matched": matched,
                "_valid": valid,
            })

        df_preview = pd.DataFrame(rows)[["File", "Sản phẩm khớp", "Hợp lệ"]]
        st.dataframe(df_preview, use_container_width=True)

        can_upload = [r for r in rows if r["_matched"] and r["_valid"]]
        st.caption(f"Có thể upload: {len(can_upload)}/{len(rows)} file")

        if can_upload and st.button(f"⬆️ Upload {len(can_upload)} Ảnh", type="primary"):
            progress = st.progress(0)
            results = []
            for i, r in enumerate(can_upload):
                res = upload_image(r["_matched"], r["_file"].getvalue(), r["_file"].name)
                results.append({
                    "File": r["File"],
                    "Sản phẩm": r["_matched"],
                    "Kết quả": "✅ Thành công" if res.get("success") else f"❌ {res.get('message')}",
                })
                progress.progress((i + 1) / len(can_upload))

            st.dataframe(pd.DataFrame(results), use_container_width=True)
            success_count = sum(1 for r in results if "✅" in r["Kết quả"])
            st.success(f"Hoàn tất: {success_count}/{len(can_upload)} ảnh đã upload!")
            st.cache_data.clear()

# ════════════════════════════════════════════════════════
# TAB 3: THƯ VIỆN ẢNH
# ════════════════════════════════════════════════════════
with tab_gallery:
    st.subheader("🖼️ Thư Viện Ảnh Sản Phẩm")

    products_with_img = [p for p in products if p.get("image_url")]
    products_no_img = [p for p in products if not p.get("image_url")]

    st.caption(f"Có ảnh: {len(products_with_img)} | Chưa có ảnh: {len(products_no_img)}")

    if products_with_img:
        cols = st.columns(4)
        for i, p in enumerate(products_with_img):
            with cols[i % 4]:
                img_url = get_image_url(p["image_url"])
                try:
                    response = requests.get(img_url, timeout=5)
                    if response.status_code == 200:
                        st.image(img_url, caption=p["item_name"], use_container_width=True)
                    else:
                        st.error(f"❌ Không tải được ảnh: {p['item_name']}")
                except Exception:
                    st.error(f"❌ Lỗi kết nối: {p['item_name']}")
    else:
        st.info("Chưa có sản phẩm nào có ảnh.")

    if products_no_img:
        with st.expander(f"📋 {len(products_no_img)} sản phẩm chưa có ảnh"):
            st.write([p["item_name"] for p in products_no_img])
