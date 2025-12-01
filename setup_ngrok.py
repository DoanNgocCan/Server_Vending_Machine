#!/usr/bin/env python3
"""
NGROK SETUP SCRIPT
Easiest way to make your vending machine server public
"""

import os
import subprocess
import sys
import time
import requests
import json
from pathlib import Path

class NgrokSetup:
    def __init__(self):
        self.ngrok_path = Path("ngrok.exe")
        self.config_path = Path.home() / ".ngrok2" / "ngrok.yml"
        
    def check_ngrok_installed(self):
        """Check if ngrok is installed"""
        return self.ngrok_path.exists()
    
    def download_ngrok(self):
        """Guide user to download ngrok"""
        print("📥 DOWNLOADING NGROK")
        print("=" * 50)
        print("1. Go to: https://ngrok.com/download")
        print("2. Click 'Download for Windows'")
        print("3. Extract ngrok.exe to this folder")
        print(f"4. Path should be: {os.getcwd()}\\ngrok.exe")
        print()
        
        input("Press Enter after downloading and extracting ngrok.exe...")
        
        if not self.check_ngrok_installed():
            print("❌ ngrok.exe not found in current directory")
            print("Please make sure ngrok.exe is in this folder")
            return False
        return True
    
    def setup_auth(self):
        """Setup ngrok authentication"""
        print("\n🔐 SETTING UP AUTHENTICATION")
        print("=" * 50)
        print("1. Go to: https://ngrok.com/signup")
        print("2. Create free account")
        print("3. Go to dashboard: https://dashboard.ngrok.com/get-started/your-authtoken")
        print("4. Copy your authtoken")
        print()
        
        auth_token = input("Enter your authtoken: ").strip()
        
        if not auth_token:
            print("❌ No authtoken provided")
            return False
        
        try:
            # Run ngrok authtoken command
            result = subprocess.run(
                [str(self.ngrok_path), "authtoken", auth_token],
                capture_output=True,
                text=True,
                check=True
            )
            print("✅ Authentication successful!")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Authentication failed: {e}")
            return False
    
    def start_tunnel(self, port=5000):
        """Start ngrok tunnel"""
        print(f"\n🚀 STARTING TUNNEL ON PORT {port}")
        print("=" * 50)
        
        # Check if Flask server is running
        try:
            response = requests.get(f"http://localhost:{port}/api/health", timeout=3)
            if response.status_code != 200:
                print(f"⚠️  Flask server might not be running on port {port}")
        except:
            print(f"⚠️  Cannot connect to Flask server on port {port}")
            print("Make sure to run: python app.py")
            print()
        
        print(f"Starting ngrok tunnel...")
        print(f"Command: {self.ngrok_path} http {port}")
        print()
        print("🌐 NGROK WILL PROVIDE PUBLIC URLS:")
        print("   - HTTP:  http://abc123.ngrok.io")
        print("   - HTTPS: https://abc123.ngrok.io")
        print()
        print("📱 UPDATE YOUR CLIENT RPIS:")
        print("   CENTRAL_SERVER_URL = 'https://abc123.ngrok.io'")
        print()
        print("🛑 TO STOP: Press Ctrl+C")
        print("=" * 50)
        
        try:
            # Start ngrok tunnel
            subprocess.run([str(self.ngrok_path), "http", str(port)])
        except KeyboardInterrupt:
            print("\n🛑 Tunnel stopped")
        except Exception as e:
            print(f"❌ Error starting tunnel: {e}")
    
    def get_tunnel_info(self):
        """Get current tunnel information"""
        try:
            response = requests.get("http://localhost:4040/api/tunnels", timeout=5)
            if response.status_code == 200:
                tunnels = response.json()
                return tunnels.get("tunnels", [])
        except:
            pass
        return []
    
    def run_setup(self):
        """Run complete setup process"""
        print("🌐 NGROK SETUP FOR VENDING MACHINE SERVER")
        print("=" * 60)
        
        # Step 1: Check if ngrok exists
        if not self.check_ngrok_installed():
            print("📥 Ngrok not found, please download it first")
            if not self.download_ngrok():
                return False
        else:
            print("✅ Ngrok found!")
        
        # Step 2: Setup authentication
        print("\n🔐 Setting up authentication...")
        if not self.setup_auth():
            return False
        
        # Step 3: Start tunnel
        self.start_tunnel()
        
        return True

if __name__ == "__main__":
    print("🎯 QUICK NGROK SETUP")
    print("This will make your vending machine server accessible from internet")
    print()
    
    setup = NgrokSetup()
    
    # Check command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "start":
            port = int(sys.argv[2]) if len(sys.argv) > 2 else 5000
            setup.start_tunnel(port)
            exit()
        elif sys.argv[1] == "auth":
            setup.setup_auth()
            exit()
    
    # Run full setup
    setup.run_setup() 