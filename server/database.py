import os
import psycopg2
import logging

logger = logging.getLogger(__name__)

# --- CẤU HÌNH ---
# Bạn có thể truyền DATABASE_URL qua biến môi trường trong Docker
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://vending:vending123@localhost:5432/vending_machine')

# --- CÁC HÀM TIỆN ÍCH DATABASE ---
def getDatabaseConnection():
    """Thiết lập kết nối đến CSDL PostgreSQL."""
    return psycopg2.connect(DATABASE_URL)

def dict_fetchone(cursor):
    """Trả về một hàng dưới dạng dict."""
    row = cursor.fetchone()
    if row is None:
        return None
    columns = [desc[0] for desc in cursor.description]
    return dict(zip(columns, row))

def dict_fetchall(cursor):
    """Trả về tất cả hàng dưới dạng list of dict."""
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]

def create_tables():
    """Tạo các bảng CSDL cần thiết khi khởi động app."""
    conn = getDatabaseConnection()
    try:
        cursor = conn.cursor()

        # 1. Bảng users
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                full_name TEXT NOT NULL,
                phone_number TEXT UNIQUE NOT NULL,
                birthday TEXT,
                password TEXT NOT NULL,
                points INTEGER DEFAULT 0,
                status TEXT DEFAULT 'active',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # 2. Bảng inventory (MASTER DATA)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                id SERIAL PRIMARY KEY,
                item_name TEXT UNIQUE NOT NULL,
                price REAL NOT NULL,
                units_sold INTEGER DEFAULT 0,
                cost_price REAL DEFAULT 0,
                description TEXT,
                image_filename TEXT,
                image_url TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS devices (
                device_id VARCHAR(50) PRIMARY KEY,
                last_active TEXT
            )
        """)

        # Migration: add image + timestamp columns to existing inventory tables
        _ALLOWED_MIGRATIONS = {
            "image_filename": "TEXT",
            "image_url":      "TEXT",
            "created_at":     "TIMESTAMP DEFAULT NOW()",
            "updated_at":     "TIMESTAMP DEFAULT NOW()",
        }
        for col, definition in _ALLOWED_MIGRATIONS.items():
            cursor.execute("""
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'inventory' AND column_name = %s
            """, (col,))
            if not cursor.fetchone():
                # col and definition are from a hardcoded allowlist — safe to interpolate
                cursor.execute(f"ALTER TABLE inventory ADD COLUMN {col} {definition}")
                logger.info("Migration: added column '%s' to inventory", col)

        # 3. Bảng device_inventory (KHO RIÊNG TỪNG MÁY)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS device_inventory (
                id SERIAL PRIMARY KEY,
                device_id TEXT NOT NULL,
                item_name TEXT NOT NULL,
                units_left INTEGER DEFAULT 0,
                last_updated TEXT,
                UNIQUE(device_id, item_name)
            )
        """)

        # 4. Bảng transactions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                transaction_id TEXT PRIMARY KEY,
                user_id TEXT,
                device_id TEXT,
                items TEXT,
                total_amount REAL NOT NULL,
                payment_method TEXT,
                payment_status TEXT,
                created_at TEXT NOT NULL,
                paid_at TEXT
            )
        """)

        # 5. Bảng giá riêng (Custom Price)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS device_pricing (
                id SERIAL PRIMARY KEY,
                device_id TEXT NOT NULL,
                item_name TEXT NOT NULL,
                custom_price REAL,
                custom_cost_price REAL,
                UNIQUE(device_id, item_name)
            )
        """)

        # 6. Thêm cột image_url vào inventory nếu chưa có
        cursor.execute("""
            ALTER TABLE inventory ADD COLUMN IF NOT EXISTS image_url TEXT
        """)

        conn.commit()
        logger.info("Database tables checked/created successfully.")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error creating tables: {e}")
        raise
    finally:
        conn.close()