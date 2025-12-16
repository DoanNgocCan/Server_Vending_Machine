# dashboard/utils.py
import pandas as pd
from services import fetch_all_transactions, fetch_products, fetch_users

def format_number(num):
    if num > 1000000: return f'{num/1000000:.2f}M'
    if num > 1000: return f'{num/1000:.2f}K'
    return f'{num:,.0f}'

def load_data():
    transactions = fetch_all_transactions()
    # Lấy Master Products để đếm số loại sản phẩm
    products = fetch_products(device_id=None) 
    users = fetch_users()
    
    # ... (Phần xử lý df_transactions giữ nguyên như code cũ) ...
    if not transactions:
        df_trans = pd.DataFrame(columns=['InvoiceNo', 'CustomerID', 'TotalPrice', 'InvoiceDate', 'Year', 'Month', 'Country'])
    else:
        df_trans = pd.DataFrame(transactions)
        rename_map = {
            'total_amount': 'TotalPrice',
            'created_at': 'InvoiceDate',
            'transaction_id': 'InvoiceNo',
            'user_id': 'CustomerID'
        }
        df_trans.rename(columns=rename_map, inplace=True)
        if 'CustomerID' not in df_trans.columns: df_trans['CustomerID'] = 'Guest'
        df_trans['InvoiceDate'] = pd.to_datetime(df_trans['InvoiceDate'])
        df_trans['Year'] = df_trans['InvoiceDate'].dt.year
        df_trans['Month'] = df_trans['InvoiceDate'].dt.month
        df_trans['Country'] = 'Vietnam'

    return {
        'df_transactions': df_trans,
        'total_products': len(products), # Số loại sản phẩm master
        'total_customers': len(users) if users else 0
    }