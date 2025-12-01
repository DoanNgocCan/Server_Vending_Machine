#!/usr/bin/env python3
"""
PUBLIC CLIENT EXAMPLE FOR RASPBERRY PI VENDING MACHINES
Connect to centralized vending machine server from anywhere on internet
"""

import requests
import json
import time
import sys
from datetime import datetime

class VendingMachineClient:
    def __init__(self, server_url, machine_id="RPi_001"):
        """
        Initialize client for remote RPi vending machine
        
        Args:
            server_url: Public URL of central server (e.g., https://abc123.ngrok.io)
            machine_id: Unique identifier for this vending machine
        """
        self.server_url = server_url.rstrip('/')
        self.machine_id = machine_id
        self.session = requests.Session()
        self.session.timeout = 10
        
        # Headers for all requests
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': f'VendingMachine-{machine_id}',
            'X-Machine-ID': machine_id
        })
    
    def test_connection(self):
        """Test connection to central server"""
        try:
            print(f"🔍 Testing connection to: {self.server_url}")
            
            # Health check
            response = self.session.get(f"{self.server_url}/api/health")
            if response.status_code == 200:
                print("✅ Central server is online")
                return True
            else:
                print(f"❌ Server returned status: {response.status_code}")
                return False
                
        except requests.exceptions.ConnectionError:
            print("❌ Cannot connect to central server")
            print("🔧 Check if:")
            print("   - Server is running")
            print("   - URL is correct")
            print("   - Internet connection is available")
            return False
        except Exception as e:
            print(f"❌ Connection error: {e}")
            return False
    
    def get_server_info(self):
        """Get server information"""
        try:
            response = self.session.get(f"{self.server_url}/api/server-info")
            if response.status_code == 200:
                info = response.json()
                print("📊 SERVER INFORMATION:")
                print(f"   Status: {info.get('status', 'Unknown')}")
                print(f"   Version: {info.get('version', 'Unknown')}")
                print(f"   Uptime: {info.get('uptime', 'Unknown')}")
                print(f"   Connected Machines: {info.get('connected_machines', 0)}")
                return info
            else:
                print(f"⚠️ Could not get server info: {response.status_code}")
                return None
        except Exception as e:
            print(f"❌ Error getting server info: {e}")
            return None
    
    def register_machine(self):
        """Register this machine with central server"""
        try:
            data = {
                "machine_id": self.machine_id,
                "location": "Unknown Location",  # Update with actual location
                "ip_address": "auto-detect",
                "capabilities": ["dispense", "payment", "facial_recognition"],
                "timestamp": datetime.now().isoformat()
            }
            
            response = self.session.post(f"{self.server_url}/api/machines/register", 
                                       json=data)
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Machine registered successfully: {result}")
                return True
            else:
                print(f"❌ Registration failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Registration error: {e}")
            return False
    
    def get_products(self):
        """Get product catalog from central server"""
        try:
            response = self.session.get(f"{self.server_url}/api/products")
            if response.status_code == 200:
                products = response.json()
                print(f"📦 Available products: {len(products)}")
                for product in products[:5]:  # Show first 5
                    print(f"   - {product.get('name')}: ${product.get('price')} (Stock: {product.get('stock')})")
                return products
            else:
                print(f"⚠️ Could not get products: {response.status_code}")
                return []
        except Exception as e:
            print(f"❌ Error getting products: {e}")
            return []
    
    def update_stock(self, product_id, quantity_dispensed):
        """Update stock after dispensing product"""
        try:
            data = {
                "machine_id": self.machine_id,
                "product_id": product_id,
                "quantity_dispensed": quantity_dispensed,
                "timestamp": datetime.now().isoformat()
            }
            
            response = self.session.post(f"{self.server_url}/api/inventory/dispense", 
                                       json=data)
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Stock updated: {result}")
                return True
            else:
                print(f"❌ Stock update failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Stock update error: {e}")
            return False
    
    def report_transaction(self, transaction_data):
        """Report completed transaction to central server"""
        try:
            # Add machine info to transaction
            transaction_data.update({
                "machine_id": self.machine_id,
                "timestamp": datetime.now().isoformat()
            })
            
            response = self.session.post(f"{self.server_url}/api/transactions", 
                                       json=transaction_data)
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Transaction reported: {result}")
                return True
            else:
                print(f"❌ Transaction report failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Transaction report error: {e}")
            return False
    
    def heartbeat(self):
        """Send heartbeat to central server"""
        try:
            data = {
                "machine_id": self.machine_id,
                "status": "online",
                "timestamp": datetime.now().isoformat()
            }
            
            response = self.session.post(f"{self.server_url}/api/heartbeat", 
                                       json=data)
            
            if response.status_code == 200:
                return True
            else:
                print(f"⚠️ Heartbeat failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Heartbeat error: {e}")
            return False
    
    def run_continuous_sync(self, interval=30):
        """Run continuous sync with central server"""
        print(f"🔄 Starting continuous sync (every {interval}s)")
        
        while True:
            try:
                # Send heartbeat
                if self.heartbeat():
                    print(f"💓 Heartbeat sent at {datetime.now()}")
                
                # Update product catalog
                products = self.get_products()
                
                # Wait for next sync
                time.sleep(interval)
                
            except KeyboardInterrupt:
                print("\n🛑 Sync stopped by user")
                break
            except Exception as e:
                print(f"❌ Sync error: {e}")
                time.sleep(interval)

def main():
    """Main function to test public server connection"""
    
    # CONFIGURATION - UPDATE THESE VALUES
    print("🔧 CONFIGURATION")
    print("=" * 50)
    
    # PUBLIC SERVER URL OPTIONS:
    
    # Option 1: Ngrok URL (easiest for testing)
    SERVER_URL = "https://abc123.ngrok.io"  # Replace with actual ngrok URL
    
    # Option 2: Cloudflare Tunnel URL
    # SERVER_URL = "https://yourdomain.cloudflare.net"
    
    # Option 3: Port Forwarding (your public IP)
    # SERVER_URL = "http://YOUR_PUBLIC_IP:5000"
    
    # Option 4: VPS deployment
    # SERVER_URL = "http://your-vps-ip:5000"
    
    # Option 5: Local network (if on same network)
    # SERVER_URL = "http://192.168.1.100:5000"
    
    MACHINE_ID = f"RPi_{time.time():.0f}"  # Unique machine ID
    
    print(f"Central Server: {SERVER_URL}")
    print(f"Machine ID: {MACHINE_ID}")
    print()
    
    # Create client
    client = VendingMachineClient(SERVER_URL, MACHINE_ID)
    
    # Test connection
    print("🚀 TESTING CONNECTION")
    print("=" * 50)
    
    if not client.test_connection():
        print("\n❌ Cannot connect to central server")
        print("🔧 Make sure:")
        print("   1. Central server is running")
        print("   2. Public tunnel is active (ngrok/cloudflare)")
        print("   3. URL is correct")
        print("   4. Internet connection is working")
        return
    
    # Get server info
    client.get_server_info()
    
    # Register machine
    print("\n📋 REGISTERING MACHINE")
    print("=" * 50)
    client.register_machine()
    
    # Get products
    print("\n📦 GETTING PRODUCT CATALOG")
    print("=" * 50)
    products = client.get_products()
    
    # Test transaction reporting
    print("\n💳 TESTING TRANSACTION REPORT")
    print("=" * 50)
    test_transaction = {
        "user_id": "test_user",
        "products": [{"id": 1, "quantity": 1, "price": 1.50}],
        "total_amount": 1.50,
        "payment_method": "cash"
    }
    client.report_transaction(test_transaction)
    
    # Continuous sync option
    print("\n🔄 CONTINUOUS SYNC OPTION")
    print("=" * 50)
    
    choice = input("Run continuous sync? (y/n): ").strip().lower()
    if choice == 'y':
        client.run_continuous_sync()
    else:
        print("✅ Connection test completed successfully!")

if __name__ == "__main__":
    print("🌐 VENDING MACHINE PUBLIC CLIENT")
    print("Connect to central server from anywhere on internet")
    print("=" * 60)
    
    # Check if URL provided as command line argument
    if len(sys.argv) > 1:
        server_url = sys.argv[1]
        machine_id = sys.argv[2] if len(sys.argv) > 2 else "RPi_CLI"
        
        client = VendingMachineClient(server_url, machine_id)
        
        if client.test_connection():
            print("✅ Connection successful!")
            client.get_server_info()
        else:
            print("❌ Connection failed!")
    else:
        # Run full test
        main() 