import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
import pandas as pd
from utils.auth import check_authentication
from utils.api_client import get_users

# Cấu hình trang
st.set_page_config(page_title="Khách Hàng — Vending Admin", page_icon="👥", layout="wide")

# Kiểm tra đăng nhập
if not check_authentication():
    st.stop()

st.title("👥 Quản Lý Khách Hàng")
st.markdown("Xem danh sách khách hàng đã đăng ký và tích điểm trên hệ thống máy bán hàng.")

# ════════════════════════════════════════════════════════
# THANH CÔNG CỤ: LÀM MỚI & TÌM KIẾM
# ════════════════════════════════════════════════════════
col_reload, col_search = st.columns([1, 3])
with col_reload:
    if st.button("🔄 Làm mới dữ liệu"):
        st.rerun()
with col_search:
    # Ô tìm kiếm sẽ tự động gọi lại trang khi người dùng gõ xong và nhấn Enter
    search_q = st.text_input("🔍 Tìm kiếm khách hàng", placeholder="Nhập tên, số điện thoại hoặc mã khách hàng...")

# ════════════════════════════════════════════════════════
# PHÂN TRANG & GỌI API
# ════════════════════════════════════════════════════════
PAGINATION_SIZE = 20
page = st.number_input("Trang", min_value=1, value=1, step=1)
offset = (page - 1) * PAGINATION_SIZE

with st.spinner("Đang tải danh sách khách hàng..."):
    # Gọi hàm get_users đã được định nghĩa sẵn trong api_client.py của bạn
    resp = get_users(limit=PAGINATION_SIZE, offset=offset, search=search_q)

# ════════════════════════════════════════════════════════
# XỬ LÝ VÀ HIỂN THỊ DỮ LIỆU
# ════════════════════════════════════════════════════════
if not resp.get("success"):
    st.error(f"❌ Lỗi: {resp.get('message', 'Không thể kết nối server')}")
else:
    users = resp.get("users", [])
    
    if not users:
        if search_q:
            st.warning(f"Không tìm thấy khách hàng nào khớp với từ khóa '{search_q}'.")
        else:
            st.info("Chưa có khách hàng nào trong hệ thống.")
    else:
        # Chuyển dữ liệu thành DataFrame của Pandas để dễ thao tác
        df = pd.DataFrame(users)
        
        # Định nghĩa các cột muốn hiển thị và tên tiếng Việt tương ứng
        rename_cols = {
            "user_id": "Mã KH",
            "full_name": "Họ và Tên",
            "phone_number": "Số điện thoại",
            "points": "Điểm tích lũy",
            "birthday": "Ngày sinh",
            "created_at": "Ngày đăng ký"
        }
        
        # Lọc ra những cột thực sự tồn tại trong API response để tránh lỗi
        show_cols = [c for c in rename_cols.keys() if c in df.columns]
        df_display = df[show_cols].rename(columns=rename_cols)

        # Xử lý định dạng thời gian (nếu cột Ngày đăng ký tồn tại)
        if "Ngày đăng ký" in df_display.columns:
            try:
                # Chuyển đổi string ISO sang định dạng ngày tháng dễ đọc
                df_display["Ngày đăng ký"] = pd.to_datetime(df_display["Ngày đăng ký"]).dt.strftime('%d/%m/%Y %H:%M')
            except Exception:
                pass # Bỏ qua nếu dữ liệu ngày tháng bị sai định dạng

        # Hiển thị bảng dữ liệu đẹp mắt
        st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True, # Ẩn cột số thứ tự mặc định của Pandas
            column_config={
                "Điểm tích lũy": st.column_config.NumberColumn("Điểm tích lũy", format="%d ✨"),
                "Mã KH": st.column_config.TextColumn("Mã KH", width="medium"),
            }
        )
        
        # Hiển thị thông tin phân trang
        total_fetched = len(users)
        st.caption(f"Đang hiển thị {total_fetched} khách hàng (Trang {page}).")