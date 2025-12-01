# dashboard/utils.py
import pandas as pd
from services import fetch_all_transactions, fetch_products, fetch_users

def format_number(num):
    if num > 1000000:
        if not isinstance(num, float): num = float(num)
        return f'{num/1000000:.2f}M'
    if num > 1000:
        if not isinstance(num, float): num = float(num)
        return f'{num/1000:.2f}K'
    return f'{num:,.0f}' # Format kiểu 10,000

def load_data():
    """
    Phiên bản load_data đã sửa lỗi KeyError khi chưa có dữ liệu.
    """
    # 1. Lấy dữ liệu thô
    transactions = fetch_all_transactions()
    products = fetch_products()
    users = fetch_users()
    
    # 2. Xử lý DataFrame Transactions
    if not transactions:
        # QUAN TRỌNG: Nếu không có giao dịch, tạo DataFrame rỗng NHƯNG CÓ ĐỊNH NGHĨA CỘT
        # Điều này giúp tránh lỗi KeyError khi truy cập cột sau này
        df_trans = pd.DataFrame(columns=['InvoiceNo', 'CustomerID', 'TotalPrice', 'InvoiceDate', 'Year', 'Month', 'Country'])
    else:
        df_trans = pd.DataFrame(transactions)
        
        # --- MAPPING CỘT ---
        # Đổi tên cột của app.py sang tên cột Dashboard mong muốn
        rename_map = {
            'total_amount': 'TotalPrice',
            'created_at': 'InvoiceDate',
            'transaction_id': 'InvoiceNo',
            'user_id': 'CustomerID'
        }
        df_trans.rename(columns=rename_map, inplace=True)

        # Kiểm tra xem cột CustomerID có tồn tại sau khi rename không (đề phòng API thiếu trường này)
        if 'CustomerID' not in df_trans.columns:
             df_trans['CustomerID'] = 'Guest' # Gán giá trị mặc định nếu thiếu

        # Xử lý dữ liệu
        df_trans['InvoiceDate'] = pd.to_datetime(df_trans['InvoiceDate'])
        df_trans['Year'] = df_trans['InvoiceDate'].dt.year
        df_trans['Month'] = df_trans['InvoiceDate'].dt.month
        
        # Tạo cột giả nếu thiếu
        if 'Country' not in df_trans.columns:
            df_trans['Country'] = 'Vietnam' 

    # 3. Tính toán số lượng khách hàng an toàn
    if users:
        total_cust = len(users)
    else:
        # Nếu không có list users, đếm từ transaction. 
        # Kiểm tra xem cột CustomerID có trong bảng không trước khi đếm
        if 'CustomerID' in df_trans.columns and not df_trans.empty:
            total_cust = df_trans['CustomerID'].nunique()
        else:
            total_cust = 0

    # 4. Trả về kết quả
    return {
        'df_transactions': df_trans,
        'total_products': len(products),
        'total_customers': total_cust
    }