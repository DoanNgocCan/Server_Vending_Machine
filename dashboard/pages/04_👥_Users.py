import sys
import os
import json # Thêm thư viện để parse chi tiết đơn hàng

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
import pandas as pd
from utils.auth import check_authentication
from utils.api_client import get_users, get_transactions # Bổ sung get_transactions

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
    # CẬP NHẬT: Thêm chữ Email vào gợi ý tìm kiếm
    search_q = st.text_input("🔍 Tìm kiếm khách hàng", placeholder="Nhập tên, số điện thoại, email hoặc mã KH...")

# ════════════════════════════════════════════════════════
# PHÂN TRANG & GỌI API KHÁCH HÀNG
# ════════════════════════════════════════════════════════
PAGINATION_SIZE = 20
page = st.number_input("Trang", min_value=1, value=1, step=1)
offset = (page - 1) * PAGINATION_SIZE

with st.spinner("Đang tải danh sách khách hàng..."):
    resp = get_users(limit=PAGINATION_SIZE, offset=offset, search=search_q)

# Lưu trữ danh sách user để dùng cho phần lịch sử giao dịch
df_users = pd.DataFrame()
selected_rows = []

# ════════════════════════════════════════════════════════
# XỬ LÝ VÀ HIỂN THỊ DỮ LIỆU KHÁCH HÀNG
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
        df_users = pd.DataFrame(users)
        
        # CẬP NHẬT: Thay đổi 'birthday' thành 'email'
        rename_cols = {
            "user_id": "Mã KH",
            "full_name": "Họ và Tên",
            "phone_number": "Số điện thoại",
            "email": "Email",              
            "points": "Điểm tích lũy",
            "created_at": "Ngày đăng ký"
        }
        
        show_cols = [c for c in rename_cols.keys() if c in df_users.columns]
        df_display = df_users[show_cols].rename(columns=rename_cols)

        if "Ngày đăng ký" in df_display.columns:
            try:
                # Ép kiểu datetime để đảm bảo hiển thị đúng
                df_display["Ngày đăng ký"] = pd.to_datetime(df_display["Ngày đăng ký"], utc=True).dt.tz_convert('Asia/Ho_Chi_Minh').dt.strftime('%d/%m/%Y %H:%M')
            except Exception:
                pass 

        event = st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True,
            on_select="rerun",           # Tự động load lại phần dưới khi click
            selection_mode="single-row", # Chỉ cho phép chọn 1 khách hàng mỗi lần
            column_config={
                "Điểm tích lũy": st.column_config.NumberColumn("Điểm tích lũy", format="%d ✨"),
                "Mã KH": st.column_config.TextColumn("Mã KH", width="medium"),
            }
        )
        
        total_fetched = len(users)
        st.caption(f"Đang hiển thị {total_fetched} khách hàng (Trang {page}). Click vào một dòng để xem lịch sử mua hàng.")
        
        # CẬP NHẬT: Chỉ gán selected_rows khi event đã thực sự được tạo
        selected_rows = event.selection.rows

# ════════════════════════════════════════════════════════
# XEM LỊCH SỬ GIAO DỊCH DỰA VÀO DÒNG ĐƯỢC CHỌN
# ════════════════════════════════════════════════════════
if selected_rows and not df_users.empty:
    st.markdown("---")
    
    # selected_rows[0] trả về index của dòng được click
    selected_index = selected_rows[0]
    selected_user_id = df_users.iloc[selected_index]["user_id"]
    selected_user_name = df_users.iloc[selected_index].get("full_name", "Khách hàng")

    st.subheader(f"🛒 Chi Tiết Giao Dịch: {selected_user_name}")
    
    with st.spinner("Đang tải lịch sử mua hàng..."):
        trans_resp = get_transactions(user_id=selected_user_id, limit=50)
        
    if not trans_resp.get("success"):
        st.error(f"Lỗi khi lấy giao dịch: {trans_resp.get('message', 'Unknown error')}")
    else:
        transactions = trans_resp.get("transactions", [])
        
        if not transactions:
            st.info("Khách hàng này chưa có giao dịch nào.")
        else:
            st.success(f"Tìm thấy {len(transactions)} đơn hàng.")
            
            for t in transactions:
                try:
                    trans_date = pd.to_datetime(t['created_at'], utc=True).tz_convert('Asia/Ho_Chi_Minh').strftime('%d/%m/%Y %H:%M')
                except:
                    trans_date = t.get('created_at', 'N/A')
                    
                amount = t.get('total_amount', 0)
                trans_id = t.get('transaction_id', 'Unknown')
                
                expander_title = f"📦 Đơn hàng: {trans_id} | 🕒 Ngày: {trans_date} | 💰 Tổng tiền: {amount:,.0f} đ"
                
                with st.expander(expander_title):
                    raw_items = t.get('items', '[]')
                    
                    if isinstance(raw_items, str):
                        try:
                            items = json.loads(raw_items)
                        except json.JSONDecodeError:
                            items = []
                    else:
                        items = raw_items
                        
                    if not items:
                        st.write("Không có chi tiết sản phẩm.")
                    else:
                        df_items = pd.DataFrame(items)
                        
                        if 'item_name' in df_items.columns:
                            df_items.rename(columns={'item_name': 'Tên sản phẩm'}, inplace=True)
                        elif 'product_name' in df_items.columns:
                            df_items.rename(columns={'product_name': 'Tên sản phẩm'}, inplace=True)
                            
                        if 'quantity' in df_items.columns:
                            df_items.rename(columns={'quantity': 'Số lượng'}, inplace=True)
                        if 'price' in df_items.columns:
                            df_items.rename(columns={'price': 'Đơn giá'}, inplace=True)
                            
                        cols_to_show = [c for c in ['Tên sản phẩm', 'Số lượng', 'Đơn giá'] if c in df_items.columns]
                        st.table(df_items[cols_to_show])