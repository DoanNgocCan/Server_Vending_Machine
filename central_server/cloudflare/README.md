# 🌐 Cloudflare Tunnel for Central Server

## 📋 Overview

This directory contains all the necessary scripts and configuration files to set up **Cloudflare Tunnel** for your Central Server, making it accessible globally via HTTPS without any network configuration.

## 🎯 Why Cloudflare Tunnel?

### Traditional Problems:
- ❌ **Port Forwarding**: Complex router configuration
- ❌ **Dynamic DNS**: IP address changes
- ❌ **Security Risks**: Open ports expose your network
- ❌ **SSL Certificates**: Manual certificate management

### Cloudflare Tunnel Solutions:
- ✅ **Zero Network Config**: No port forwarding needed
- ✅ **Global Access**: Works from anywhere
- ✅ **Automatic SSL**: Free, managed certificates
- ✅ **Enterprise Security**: DDoS protection included

## 🚀 Quick Start (5 Minutes)

### Prerequisites
1. **Domain Name**: You need a domain (can be purchased for ~$10/year)
2. **Cloudflare Account**: Free account at cloudflare.com
3. **Running Central Server**: Your Flask app should be running on port 5000

### Super Quick Setup
```bash
# Copy script to your Raspberry Pi
scp quick_setup.sh pi@your-rpi-ip:~/

# SSH to your Pi and run
chmod +x ~/quick_setup.sh
./quick_setup.sh

# Follow the prompts:
# 1. Enter your domain (e.g., example.com)
# 2. Enter subdomain (e.g., rpi)
# 3. Authenticate with Cloudflare (browser opens)
# 4. Wait for setup to complete

# Your server is now live at: https://rpi.example.com
```

## 📁 Files Explained

### Scripts
- **`quick_setup.sh`** - 5-minute automated setup for experienced users
- **`setup_tunnel.sh`** - Full setup with detailed logging and error handling

### Configuration
- **`config.yml.example`** - Template showing all available configuration options
- **`CLOUDFLARE_TUNNEL_GUIDE.md`** - Complete step-by-step guide

### Generated Files (on RPi)
- **`~/.cloudflared/config.yml`** - Your actual tunnel configuration
- **`~/.cloudflared/cert.pem`** - Authentication certificate
- **`~/.cloudflared/{tunnel-id}.json`** - Tunnel credentials
- **`~/tunnel_control.sh`** - Management script for daily operations

## 🛠️ Setup Options

### Option 1: Quick Setup (Recommended)
**For users comfortable with command line:**
```bash
./quick_setup.sh
```
- **Time**: ~5 minutes
- **Interaction**: Minimal prompts
- **Best for**: Getting up and running quickly

### Option 2: Detailed Setup
**For users who want full control:**
```bash
./setup_tunnel.sh
```
- **Time**: ~10-15 minutes
- **Interaction**: Detailed prompts and explanations
- **Best for**: Understanding each step

### Option 3: Manual Setup
**For learning or troubleshooting:**
Follow the complete guide in `CLOUDFLARE_TUNNEL_GUIDE.md`
- **Time**: ~30-60 minutes
- **Interaction**: Full manual control
- **Best for**: Learning the process or custom configurations

## 📊 What Happens During Setup

1. **Domain Verification**: Checks if you have a domain in Cloudflare
2. **Cloudflared Installation**: Downloads and installs the tunnel client
3. **Authentication**: Links your Pi to your Cloudflare account
4. **Tunnel Creation**: Creates a secure tunnel connection
5. **DNS Configuration**: Sets up automatic DNS routing
6. **Service Installation**: Configures tunnel to start automatically
7. **Testing**: Verifies everything is working

## 🔧 Daily Management

### Common Commands
```bash
# Check if tunnel is running
~/bin/tunnel status

# View live logs
~/bin/tunnel logs

# Restart tunnel
~/bin/tunnel restart

# Test connectivity
~/bin/tunnel test

# Get your public URL
~/bin/tunnel url
```

### Service Management
```bash
# Start/stop tunnel service
sudo systemctl start cloudflared
sudo systemctl stop cloudflared

# Check detailed service status
sudo systemctl status cloudflared

# View service logs
sudo journalctl -u cloudflared -f
```

## 🌍 Example Use Cases

### 1. Remote IoT Monitoring
```bash
# From anywhere in the world:
curl https://rpi.yourdomain.com/api/stats
```

### 2. Mobile App Integration
```javascript
// In your mobile app
const API_BASE = 'https://rpi.yourdomain.com/api';
const response = await fetch(`${API_BASE}/device/sensor-001/latest`);
```

### 3. Third-Party Integrations
```python
import requests

# Send data from remote devices
data = {
    "device_id": "remote-sensor-01",
    "type": "sensor",
    "payload": {"temperature": 23.5, "humidity": 67}
}

response = requests.post(
    "https://rpi.yourdomain.com/api/device/data",
    json=data
)
```

## 🔐 Security Features

### Built-in Protection
- **DDoS Mitigation**: Automatic protection against attacks
- **SSL/TLS Encryption**: All traffic encrypted
- **Access Logs**: Monitor who accesses your server
- **Rate Limiting**: Prevent abuse

### Optional Enhancements
- **Access Policies**: Restrict access by country/IP
- **Zero Trust**: Require authentication for admin endpoints
- **Webhook Security**: Verify webhook signatures

## 🚨 Troubleshooting

### Common Issues & Solutions

**Tunnel Not Starting:**
```bash
# Check config syntax
cloudflared tunnel ingress validate

# Check service logs
sudo journalctl -u cloudflared -n 50
```

**DNS Not Resolving:**
```bash
# Check DNS propagation
dig rpi.yourdomain.com +trace

# Test with Cloudflare DNS
nslookup rpi.yourdomain.com 1.1.1.1
```

**Connection Timeouts:**
```bash
# Verify Central Server is running
curl localhost:5000/

# Check tunnel config
cat ~/.cloudflared/config.yml
```

### Getting Help
1. **Check Logs**: `sudo journalctl -u cloudflared -f`
2. **Test Locally**: `curl localhost:5000/`
3. **Verify DNS**: `dig rpi.yourdomain.com`
4. **Read Guide**: Review `CLOUDFLARE_TUNNEL_GUIDE.md`

## 📈 Performance Tips

### Optimize Configuration
```yaml
# Add to ~/.cloudflared/config.yml
http2-origin: true
chunked-encoding: true
compression-quality: 0
keep-alive-connections: 100
keep-alive-timeout: 90s
```

### Monitor Performance
```bash
# Enable metrics endpoint
echo "metrics: 0.0.0.0:2000" >> ~/.cloudflared/config.yml

# View metrics
curl localhost:2000/metrics
```

## 💰 Cost Information

### Free Tier Includes:
- ✅ **Unlimited Bandwidth**: No traffic limits
- ✅ **SSL Certificates**: Automatic renewal
- ✅ **DDoS Protection**: Basic protection
- ✅ **DNS Management**: Full DNS control
- ✅ **Multiple Tunnels**: No limit on tunnels

### Only Cost:
- **Domain Registration**: ~$10-15/year
- **Everything Else**: Completely free!

## 🔄 Updating & Maintenance

### Update Cloudflared
```bash
# Check current version
cloudflared --version

# Update to latest
wget -O /tmp/cloudflared https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64
sudo mv /tmp/cloudflared /usr/local/bin/cloudflared
chmod +x /usr/local/bin/cloudflared

# Restart service
sudo systemctl restart cloudflared
```

### Backup Configuration
```bash
# Backup tunnel configuration
tar -czf cloudflared-backup.tar.gz ~/.cloudflared/

# Store backup safely
scp cloudflared-backup.tar.gz user@backup-server:~/backups/
```

## 🎉 Success Metrics

After successful setup, you should have:
- ✅ **Global HTTPS URL**: `https://subdomain.yourdomain.com`
- ✅ **Zero Downtime**: Tunnel reconnects automatically
- ✅ **Fast Performance**: Global CDN acceleration
- ✅ **Enterprise Security**: DDoS protection active
- ✅ **Easy Management**: Simple commands for daily operations

## 📞 Support Resources

- **Cloudflare Tunnel Docs**: [developers.cloudflare.com/cloudflare-one/connections/connect-apps](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps)
- **Community Forum**: [community.cloudflare.com](https://community.cloudflare.com)
- **Status Page**: [cloudflarestatus.com](https://cloudflarestatus.com)

---

**🚀 Ready to make your Central Server globally accessible? Run `./quick_setup.sh` and get online in 5 minutes!** 