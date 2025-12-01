-- -- Database schema for Central Server
-- -- This schema defines the structure for storing device information and data logs

-- -- Table for registering devices
-- CREATE TABLE IF NOT EXISTS devices (
--     device_id TEXT PRIMARY KEY,
--     device_name TEXT NOT NULL,
--     device_type TEXT NOT NULL,
--     description TEXT,
--     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
--     updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
--     status TEXT DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'maintenance'))
-- );

-- -- Table for storing device data logs
-- CREATE TABLE IF NOT EXISTS device_data_logs (
--     id INTEGER PRIMARY KEY AUTOINCREMENT,
--     device_id TEXT NOT NULL,
--     data_type TEXT NOT NULL,
--     timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
--     payload TEXT NOT NULL, -- JSON format
--     received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
--     FOREIGN KEY (device_id) REFERENCES devices(device_id)
-- );

-- -- Create indexes for better performance
-- CREATE INDEX IF NOT EXISTS idx_device_data_logs_device_id ON device_data_logs(device_id);
-- CREATE INDEX IF NOT EXISTS idx_device_data_logs_timestamp ON device_data_logs(timestamp);
-- CREATE INDEX IF NOT EXISTS idx_device_data_logs_data_type ON device_data_logs(data_type);

-- -- Sample data for testing
-- INSERT OR IGNORE INTO devices (device_id, device_name, device_type, description) VALUES
-- ('rpi-001', 'Raspberry Pi Sensor Hub 1', 'sensor', 'Temperature and humidity sensor hub'),
-- ('rpi-002', 'Raspberry Pi Camera Node', 'camera', 'Security camera monitoring system'),
-- ('esp32-001', 'ESP32 Environmental Monitor', 'sensor', 'Environmental monitoring device');

-- -- Sample data logs for testing
-- INSERT OR IGNORE INTO device_data_logs (device_id, data_type, payload) VALUES
-- ('rpi-001', 'sensor', '{"temp": 28.5, "humidity": 72, "location": "living_room"}'),
-- ('rpi-001', 'sensor', '{"temp": 29.1, "humidity": 70, "location": "living_room"}'),
-- ('esp32-001', 'sensor', '{"temp": 25.3, "humidity": 65, "pressure": 1013.25}'); 

CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    full_name TEXT NOT NULL,
    phone_number TEXT NOT NULL,
    email TEXT,
    device_id TEXT,
    status TEXT DEFAULT 'active',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS face_embeddings (
    embedding_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    embedding_data TEXT NOT NULL, -- JSON string
    confidence_score REAL DEFAULT 0.95,
    device_id TEXT,
    created_at TEXT NOT NULL,
    is_active BOOLEAN DEFAULT 1,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS products (
    product_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT,
    price REAL NOT NULL,
    stock INTEGER NOT NULL,
    slot_number INTEGER,
    is_active BOOLEAN DEFAULT 1,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS transactions (
    transaction_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    device_id TEXT,
    items TEXT NOT NULL, -- JSON array of cart items
    total_amount REAL NOT NULL,
    payment_method TEXT,
    payment_status TEXT DEFAULT 'pending',
    created_at TEXT NOT NULL,
    paid_at TEXT,
    location TEXT,
    metadata TEXT,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);
CREATE TABLE IF NOT EXISTS devices (
    device_id TEXT PRIMARY KEY,
    device_name TEXT NOT NULL,
    device_type TEXT NOT NULL,
    description TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS device_data (
    data_id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT NOT NULL,
    data_type TEXT,
    payload TEXT NOT NULL, -- JSON string
    timestamp TEXT NOT NULL,
    FOREIGN KEY (device_id) REFERENCES devices(device_id)
);
