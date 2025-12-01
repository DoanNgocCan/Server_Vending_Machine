from datetime import datetime
import sqlite3
import os
import json

DB_PATH = os.path.join(os.path.dirname(__file__), 'central_server.db')

def getDatabaseConnection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def getAllDevices():
    try:
        conn = getDatabaseConnection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM devices")
        devices = cursor.fetchall()
        conn.close()
        return [dict(device) for device in devices]
    except Exception as e:
        raise Exception(f"Error retrieving devices: {str(e)}")

def getDeviceInfo(device_id):
    try:
        conn = getDatabaseConnection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM devices WHERE device_id = ?", (device_id,))
        device = cursor.fetchone()
        conn.close()
        return dict(device) if device else None
    except Exception as e:
        raise Exception(f"Error retrieving device info: {str(e)}")

def registerDevice(device_id, device_name, device_type, description):
    try:
        conn = getDatabaseConnection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO devices (device_id, device_name, device_type, description)
            VALUES (?, ?, ?, ?)
        """, (device_id, device_name, device_type, description))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        raise Exception(f"Error registering device: {str(e)}")

def insertDeviceData(device_id, data_type, payload, timestamp=None):
    try:
        conn = getDatabaseConnection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO device_data (device_id, data_type, payload, timestamp)
            VALUES (?, ?, ?, ?)
        """, (device_id, data_type, json.dumps(payload), timestamp or datetime.now().isoformat()))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        raise Exception(f"Error inserting device data: {str(e)}")

def getDeviceData(device_id, limit=100, data_type=None):
    try:
        conn = getDatabaseConnection()
        cursor = conn.cursor()
        query = "SELECT * FROM device_data WHERE device_id = ?"
        params = [device_id]
        
        if data_type:
            query += " AND data_type = ?"
            params.append(data_type)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        data = cursor.fetchall()
        conn.close()
        return [dict(record) for record in data]
    except Exception as e:
        raise Exception(f"Error retrieving device data: {str(e)}")

def getLatestDeviceData(device_id, data_type=None):
    try:
        conn = getDatabaseConnection()
        cursor = conn.cursor()
        query = "SELECT * FROM device_data WHERE device_id = ?"
        params = [device_id]
        
        if data_type:
            query += " AND data_type = ?"
            params.append(data_type)
        
        query += " ORDER BY timestamp DESC LIMIT 1"
        cursor.execute(query, params)
        data = cursor.fetchone()
        conn.close()
        return dict(data) if data else None
    except Exception as e:
        raise Exception(f"Error retrieving latest device data: {str(e)}")

def getAllProducts():
    try:
        conn = getDatabaseConnection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products WHERE is_active = 1 AND stock > 0")
        products = cursor.fetchall()
        conn.close()
        return [dict(product) for product in products]
    except Exception as e:
        raise Exception(f"Error retrieving products: {str(e)}")

def getUserById(user_id):
    try:
        conn = getDatabaseConnection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        conn.close()
        return dict(user) if user else None
    except Exception as e:
        raise Exception(f"Error retrieving user: {str(e)}")