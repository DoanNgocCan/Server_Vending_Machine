#!/usr/bin/env python3
"""
PUBLIC SERVER SETUP GUIDE
Transform this machine into a publicly accessible vending machine server
"""

import os
import subprocess
import requests
import socket
import json
from datetime import datetime

print("=" * 80)
print("🌐 VENDING MACHINE PUBLIC SERVER SETUP")
print("=" * 80)

def get_local_ip():
    """Get local IP address"""
    try:
        # Connect to external server to get local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except:
        return "Unable to detect"

def check_port_open(port=5000):
    """Check if Flask server is running"""
    try:
        response = requests.get(f"http://localhost:{port}/api/health", timeout=3)
        return response.status_code == 200
    except:
        return False

def get_public_ip():
    """Get public IP address"""
    try:
        response = requests.get("https://api.ipify.org", timeout=5)
        return response.text.strip()
    except:
        return "Unable to detect"

# System Information
print(f"📋 SYSTEM INFORMATION")
print(f"   Local IP: {get_local_ip()}")
print(f"   Public IP: {get_public_ip()}")
print(f"   Flask Server: {'✅ Running' if check_port_open() else '❌ Not running'}")
print(f"   Timestamp: {datetime.now()}")

print("\n" + "=" * 80)
print("🚀 DEPLOYMENT OPTIONS FOR PUBLIC ACCESS")
print("=" * 80)

print("""
## OPTION 1: NGROK (RECOMMENDED - Easiest)
✅ Pros: Easy setup, HTTPS included, no router config needed
❌ Cons: URL changes on restart (free tier)

### Steps:
1. Download Ngrok: https://ngrok.com/download
2. Extract ngrok.exe to this folder
3. Sign up for free account: https://ngrok.com/signup
4. Get auth token from dashboard
5. Run: ngrok authtoken YOUR_TOKEN
6. Run: ngrok http 5000

### Commands:
```
# Download and setup (manual)
# 1. Go to https://ngrok.com/download
# 2. Download Windows version
# 3. Extract ngrok.exe here

# Authentication
ngrok authtoken YOUR_AUTH_TOKEN

# Start tunnel
ngrok http 5000
```

### Result:
- Public URL: https://abc123.ngrok.io
- All RPi devices use this URL
- Works from anywhere with internet
""")

print("""
## OPTION 2: CLOUDFLARE TUNNEL (Free, Permanent URL)
✅ Pros: Free, permanent URL, secure
❌ Cons: Slightly more complex setup

### Steps:
1. Install Cloudflare: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/
2. Run: cloudflared tunnel --url http://localhost:5000

### Commands:
```
# Install cloudflared (download from Cloudflare)
cloudflared tunnel --url http://localhost:5000
```
""")

print("""
## OPTION 3: PORT FORWARDING (Traditional)
✅ Pros: Direct access, no third party
❌ Cons: Requires router access, security considerations

### Steps:
1. Access router admin (usually 192.168.1.1)
2. Find "Port Forwarding" section
3. Forward port 5000 to this machine's IP
4. Use public IP: http://YOUR_PUBLIC_IP:5000

### Router Config:
- External Port: 5000
- Internal IP: {get_local_ip()}
- Internal Port: 5000
- Protocol: TCP

### Security (IMPORTANT):
- Setup firewall rules
- Use HTTPS (SSL certificates)
- Implement API authentication
""")

print("""
## OPTION 4: VPS DEPLOYMENT (Professional)
✅ Pros: Full control, permanent, scalable
❌ Cons: Costs money, requires setup

### Popular VPS Providers:
- DigitalOcean: $5/month
- Linode: $5/month  
- AWS EC2: Free tier available
- Google Cloud: Free tier available

### Deployment Steps:
1. Create VPS instance
2. Upload code to VPS
3. Install dependencies
4. Run server on VPS
5. Use VPS IP as central server
""")

print("""
## OPTION 5: RASPBERRY PI HOTSPOT (Offline Network)
✅ Pros: Complete control, no internet dependency
❌ Cons: Limited range, requires WiFi setup

### Setup:
1. Configure Pi as WiFi Access Point
2. All other RPi connect to this AP
3. Local network: 192.168.4.x
4. Central server: 192.168.4.1:5000

### Commands:
```
# Install hostapd and dnsmasq
sudo apt install hostapd dnsmasq

# Configure AP mode
sudo systemctl enable hostapd
sudo systemctl enable dnsmasq
```
""")

print("\n" + "=" * 80)
print("🔧 QUICK START RECOMMENDATIONS")
print("=" * 80)

print("""
### FOR TESTING/DEVELOPMENT:
→ Use NGROK (Option 1)
  - Quick setup
  - Works immediately
  - Good for demos

### FOR PRODUCTION:
→ Use VPS (Option 4) or Cloudflare Tunnel (Option 2)
  - Reliable
  - Permanent URLs
  - Professional setup

### FOR OFFLINE DEPLOYMENT:
→ Use RPi Hotspot (Option 5)
  - No internet required
  - Complete control
  - Local network only
""")

print(f"""
## EXAMPLE CLIENT CONFIG FOR RPIS:
```python
# Update in client_example.py
CENTRAL_SERVER_URL = "https://abc123.ngrok.io"  # Ngrok URL
# OR
CENTRAL_SERVER_URL = "https://yourdomain.cloudflare.net"  # Cloudflare URL  
# OR
CENTRAL_SERVER_URL = "http://{get_public_ip()}:5000"  # Port forwarding
# OR
CENTRAL_SERVER_URL = "http://your-vps-ip:5000"  # VPS deployment
```
""")

print("\n" + "=" * 80)
print("📞 CURRENT SERVER STATUS")
print("=" * 80)

if check_port_open():
    print("✅ Flask server is running on port 5000")
    print(f"🌐 Local access: http://{get_local_ip()}:5000")
    print("🚀 Ready for public deployment!")
else:
    print("❌ Flask server is not running")
    print("⚠️  Start server first: python app.py")

print("\n" + "=" * 80)
print("🎯 NEXT STEPS")
print("=" * 80)
print("1. Choose deployment method above")
print("2. Follow setup instructions")
print("3. Update client_example.py with public URL")
print("4. Test connection from external device")
print("5. Deploy to other Raspberry Pi devices")
print("=" * 80) 