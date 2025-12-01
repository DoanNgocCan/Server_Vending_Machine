"""
Database handler for Central Server
This module handles all database operations for the central server system
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import List, Dict, Optional, Union, Any

# Database configuration
DB_FILE = os.path.join(os.path.dirname(__file__), '..', 'central_server.db')
SCHEMA_FILE = os.path.join(os.path.dirname(__file__), 'schema.sql')

class DatabaseHandler:
    """
    Database handler class for managing SQLite operations
    """
    
    def __init__(self, db_path: str = DB_FILE):
        """
        Initialize database handler
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.initializeDatabase()
    
    def initializeDatabase(self):
        """
        Initialize database with schema if it doesn't exist
        """
        try:
            with open(SCHEMA_FILE, 'r') as schema_file:
                schema_sql = schema_file.read()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.executescript(schema_sql)
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error initializing database: {e}")
            raise
    
    def executeSelectQuery(self, query: str, params: tuple = (), fetch_one: bool = False) -> Union[List[Dict], Dict, None]:
        """
        Execute a SELECT query
        
        Args:
            query: SQL SELECT query string
            params: Query parameters
            fetch_one: Whether to fetch only one result
            
        Returns:
            Query results or None
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Return rows as dictionaries
            cursor = conn.cursor()
            
            cursor.execute(query, params)
            
            if fetch_one:
                result = cursor.fetchone()
                return dict(result) if result else None
            else:
                results = cursor.fetchall()
                return [dict(row) for row in results]
                
        except Exception as e:
            print(f"Database query error: {e}")
            return None
        finally:
            conn.close()
    
    def executeNonSelectQuery(self, query: str, params: tuple = ()) -> int:
        """
        Execute a non-SELECT query (INSERT, UPDATE, DELETE)
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            Number of affected rows
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount
                
        except Exception as e:
            print(f"Database query error: {e}")
            return 0
        finally:
            conn.close()
    
    def insertDeviceData(self, device_id: str, data_type: str, payload: Dict, timestamp: Optional[str] = None) -> bool:
        """
        Insert device data into database
        
        Args:
            device_id: Device identifier
            data_type: Type of data (sensor, camera, etc.)
            payload: Data payload as dictionary
            timestamp: Optional timestamp (ISO format)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            payload_json = json.dumps(payload)
            
            if timestamp:
                query = """
                INSERT INTO device_data_logs (device_id, data_type, payload, timestamp)
                VALUES (?, ?, ?, ?)
                """
                params = (device_id, data_type, payload_json, timestamp)
            else:
                query = """
                INSERT INTO device_data_logs (device_id, data_type, payload)
                VALUES (?, ?, ?)
                """
                params = (device_id, data_type, payload_json)
            
            result = self.executeNonSelectQuery(query, params)
            return result > 0
            
        except Exception as e:
            print(f"Error inserting device data: {e}")
            return False
    
    def getDeviceData(self, device_id: str, limit: int = 100, data_type: Optional[str] = None) -> List[Dict]:
        """
        Get device data from database
        
        Args:
            device_id: Device identifier
            limit: Maximum number of records to return
            data_type: Optional filter by data type
            
        Returns:
            List of device data records
        """
        try:
            if data_type:
                query = """
                SELECT * FROM device_data_logs
                WHERE device_id = ? AND data_type = ?
                ORDER BY timestamp DESC
                LIMIT ?
                """
                params = (device_id, data_type, limit)
            else:
                query = """
                SELECT * FROM device_data_logs
                WHERE device_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
                """
                params = (device_id, limit)
            
            results = self.executeSelectQuery(query, params)
            
            # Parse JSON payload in each result
            if results and isinstance(results, list):
                for result in results:
                    try:
                        result['payload'] = json.loads(result['payload'])
                    except:
                        pass
                return results
            
            return []
            
        except Exception as e:
            print(f"Error getting device data: {e}")
            return []
    
    def getLatestDeviceData(self, device_id: str, data_type: Optional[str] = None) -> Optional[Dict]:
        """
        Get the latest data for a device
        
        Args:
            device_id: Device identifier
            data_type: Optional filter by data type
            
        Returns:
            Latest device data record or None
        """
        data = self.getDeviceData(device_id, limit=1, data_type=data_type)
        return data[0] if data else None
    
    def registerDevice(self, device_id: str, device_name: str, device_type: str, description: str = "") -> bool:
        """
        Register a new device
        
        Args:
            device_id: Unique device identifier
            device_name: Human-readable device name
            device_type: Type of device
            description: Device description
            
        Returns:
            True if successful, False otherwise
        """
        try:
            query = """
            INSERT OR REPLACE INTO devices (device_id, device_name, device_type, description, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """
            params = (device_id, device_name, device_type, description)
            
            result = self.executeNonSelectQuery(query, params)
            return result > 0
            
        except Exception as e:
            print(f"Error registering device: {e}")
            return False
    
    def getAllDevices(self) -> List[Dict]:
        """
        Get all registered devices
        
        Returns:
            List of all devices
        """
        try:
            query = "SELECT * FROM devices ORDER BY created_at DESC"
            results = self.executeSelectQuery(query)
            return results if isinstance(results, list) else []
            
        except Exception as e:
            print(f"Error getting all devices: {e}")
            return []
    


    def getDeviceInfo(self, device_id: str) -> Optional[Dict]:
        """
        Get device information
        
        Args:
            device_id: Device identifier
            
        Returns:
            Device information or None
        """
        try:
            query = "SELECT * FROM devices WHERE device_id = ?"
            result = self.executeSelectQuery(query, (device_id,), fetch_one=True)
            return result if isinstance(result, dict) else None
            
        except Exception as e:
            print(f"Error getting device info: {e}")
            return None
    
    def getDatabaseConnection(self):
        """
        Get a database connection
        
        Returns:
            SQLite connection object
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

# Global database handler instance
db_handler = DatabaseHandler()