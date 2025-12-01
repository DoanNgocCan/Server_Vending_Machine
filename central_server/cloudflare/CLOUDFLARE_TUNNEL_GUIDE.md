# 🌐 Cloudflare Tunnel Setup Guide

## 📋 Overview

This guide walks you through setting up **Cloudflare Tunnel** to make your Central Server accessible from anywhere on the internet without opening ports or configuring port forwarding.

### 🎯 What You'll Achieve

- ✅ **Secure Access**: No open ports on your router
- ✅ **Global Accessibility**: Access your RPi from anywhere
- ✅ **Free SSL**: Automatic HTTPS encryption
- ✅ **Custom Domain**: Use your own domain name
- ✅ **DDoS Protection**: Cloudflare's built-in protection

---

## 🕐 Time Requirements

| Phase | Tasks | Estimated Time |
|-------|-------|---------------|
| **2.1** | Create Cloudflare Account | 15-20 minutes |
| **2.2** | Add Domain to Cloudflare | 30-45 minutes |
| **2.3** | Install Cloudflare Tunnel | 15-20 minutes |
| **2.4** | Authenticate with Cloudflare | 10-15 minutes |
| **2.5** | Create Tunnel & Configure DNS | 20-30 minutes |
| **2.6** | Setup as System Service | 15-20 minutes |
| **Total** | **Complete Setup** | **~2-3 hours** |

---

## 🧱 Phase 2.1: Create Cloudflare Account

### Step 2.1.1: Access Cloudflare
```bash
# Open in browser
https://cloudflare.com
```

### Step 2.1.2: Register Account
1. Click **"Sign Up"**
2. Enter your email address
3. Create a strong password
4. Verify your email address
5. Complete any additional verification steps

### Step 2.1.3: Login Successfully
- Access the Cloudflare dashboard
- Familiarize yourself with the interface

---

## 🏠 Phase 2.2: Add Domain to Cloudflare

### Step 2.2.1: Register Domain (if needed)
**Popular Domain Registrars:**
- [Namecheap](https://namecheap.com) - Recommended
- [GoDaddy](https://godaddy.com)
- [Google Domains](https://domains.google)
- [Cloudflare Registrar](https://www.cloudflare.com/products/registrar/)

**Budget Options:**
- `.com` domains: $8-12/year
- `.net` domains: $10-15/year
- `.org` domains: $12-18/year

### Step 2.2.2: Add Domain to Cloudflare
1. In Cloudflare dashboard, click **"Add site"**
2. Enter your domain name (e.g., `example.com`)
3. Select **"Free"** plan
4. Click **"Add site"**

### Step 2.2.3: Update Nameservers
1. Cloudflare will provide 2 nameservers like:
   ```
   alice.ns.cloudflare.com
   bob.ns.cloudflare.com
   ```
2. Go to your domain registrar's control panel
3. Update nameservers to Cloudflare's nameservers
4. Save changes

### Step 2.2.4: Verify DNS Propagation
```bash
# Check if nameservers have updated
nslookup -type=NS example.com

# Check if Cloudflare is managing DNS
dig example.com

# Wait for propagation (can take 24-48 hours)
```

---

## 🔧 Phase 2.3: Install Cloudflare Tunnel on RPi

### Step 2.3.1: Automated Installation
```bash
# Copy the setup script to your RPi
scp central_server/cloudflare/setup_tunnel.sh pi@your-rpi-ip:~/

# Make executable
chmod +x ~/setup_tunnel.sh

# Run the setup script
./setup_tunnel.sh
```

### Step 2.3.2: Manual Installation (Alternative)
```bash
# Download cloudflared for ARM64 (RPi 4)
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64

# For ARM7 (older RPi)
# wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm

# Make executable and install
chmod +x cloudflared-linux-arm64
sudo mv cloudflared-linux-arm64 /usr/local/bin/cloudflared

# Verify installation
cloudflared --version
```

---

## 🔐 Phase 2.4: Authenticate with Cloudflare

### Step 2.4.1: Start Authentication
```bash
# This will open a browser window
cloudflared tunnel login
```

### Step 2.4.2: Complete Browser Authentication
1. Browser opens to Cloudflare login
2. Login with your Cloudflare credentials
3. **Select your domain** from the list
4. Click **"Authorize"**

### Step 2.4.3: Verify Authentication
```bash
# Check if certificate file exists
ls -la ~/.cloudflared/cert.pem

# Should show something like:
# -rw------- 1 pi pi 2484 Jan 10 12:34 /home/pi/.cloudflared/cert.pem
```

---

## 🛠️ Phase 2.5: Create Tunnel & Configure DNS

### Step 2.5.1: Create Tunnel
```bash
# Create a new tunnel
cloudflared tunnel create rpi-central

# Note the Tunnel ID that appears
# Example: Created tunnel rpi-central with id: 12345678-1234-1234-1234-123456789012
```

### Step 2.5.2: Create Configuration File
```bash
# Create config directory
mkdir -p ~/.cloudflared

# Create config file
nano ~/.cloudflared/config.yml
```

**Example Configuration:**
```yaml
tunnel: 12345678-1234-1234-1234-123456789012
credentials-file: /home/pi/.cloudflared/12345678-1234-1234-1234-123456789012.json

ingress:
  - hostname: rpi.yourdomain.com
    service: http://localhost:5000
  - service: http_status:404
```

### Step 2.5.3: Configure DNS
```bash
# Route your subdomain to the tunnel
cloudflared tunnel route dns rpi-central rpi.yourdomain.com

# Verify DNS record was created
dig rpi.yourdomain.com
```

### Step 2.5.4: Test Tunnel (Manual)
```bash
# Start tunnel manually for testing
cloudflared tunnel run rpi-central

# In another terminal or browser, test:
curl https://rpi.yourdomain.com/
```

---

## 🚀 Phase 2.6: Setup as System Service

### Step 2.6.1: Install Service
```bash
# Install cloudflared as a service
sudo cloudflared service install --config=/home/pi/.cloudflared/config.yml
```

### Step 2.6.2: Enable and Start Service
```bash
# Enable service to start at boot
sudo systemctl enable cloudflared

# Start the service
sudo systemctl start cloudflared

# Check service status
sudo systemctl status cloudflared
```

### Step 2.6.3: Verify Service Logs
```bash
# Check service logs
sudo journalctl -u cloudflared -f

# Should show something like:
# Jan 10 12:34:56 raspberrypi cloudflared[1234]: Registered tunnel connection
```

### Step 2.6.4: Create Management Scripts
```bash
# Create tunnel management script
cat > ~/tunnel_control.sh << 'EOF'
#!/bin/bash
case "$1" in
    start)   sudo systemctl start cloudflared ;;
    stop)    sudo systemctl stop cloudflared ;;
    restart) sudo systemctl restart cloudflared ;;
    status)  sudo systemctl status cloudflared ;;
    logs)    sudo journalctl -u cloudflared -f ;;
    test)    curl -s https://rpi.yourdomain.com/ ;;
    *) echo "Usage: $0 {start|stop|restart|status|logs|test}" ;;
esac
EOF

# Make executable
chmod +x ~/tunnel_control.sh

# Create symbolic link
ln -s ~/tunnel_control.sh ~/bin/tunnel
```

---

## 🧪 Testing & Verification

### Test All Endpoints
```bash
# Health check
curl https://rpi.yourdomain.com/

# Register a device
curl -X POST https://rpi.yourdomain.com/api/devices \
  -H "Content-Type: application/json" \
  -d '{"device_id": "test-device", "device_name": "Test Device", "device_type": "sensor"}'

# Send test data
curl -X POST https://rpi.yourdomain.com/api/device/data \
  -H "Content-Type: application/json" \
  -d '{"device_id": "test-device", "type": "sensor", "payload": {"temp": 25.5, "humidity": 60}}'

# Get device data
curl https://rpi.yourdomain.com/api/device/test-device/data
```

### Test from External Network
```bash
# Test from your phone/laptop on different network
curl https://rpi.yourdomain.com/api/stats

# Or open in browser
https://rpi.yourdomain.com/
```

---

## 📊 Management Commands

### Daily Operations
```bash
# Check tunnel status
~/tunnel_control.sh status

# View live logs
~/tunnel_control.sh logs

# Restart tunnel
~/tunnel_control.sh restart

# Test connectivity
~/tunnel_control.sh test
```

### Troubleshooting
```bash
# Check tunnel list
cloudflared tunnel list

# Check DNS settings
dig rpi.yourdomain.com

# Check service status
sudo systemctl status cloudflared

# Check configuration
cat ~/.cloudflared/config.yml

# Manual tunnel run for debugging
cloudflared tunnel run rpi-central
```

---

## 🔐 Security Considerations

### 1. **Access Control**
```yaml
# Add IP restrictions in config.yml
ingress:
  - hostname: rpi.yourdomain.com
    service: http://localhost:5000
    originRequest:
      connectTimeout: 30s
      tlsTimeout: 10s
```

### 2. **Rate Limiting**
- Implement rate limiting in your Flask app
- Use Cloudflare's rate limiting rules

### 3. **Authentication**
- Add API key authentication to sensitive endpoints
- Consider OAuth integration for admin access

### 4. **Monitoring**
- Enable Cloudflare Analytics
- Set up alerts for unusual traffic patterns

---

## 🚨 Troubleshooting Common Issues

### Issue 1: Tunnel Not Starting
```bash
# Check config syntax
cloudflared tunnel ingress validate

# Check credentials
ls -la ~/.cloudflared/

# Check service logs
sudo journalctl -u cloudflared -n 50
```

### Issue 2: DNS Not Resolving
```bash
# Check DNS propagation
dig rpi.yourdomain.com +trace

# Check Cloudflare DNS settings
nslookup rpi.yourdomain.com 1.1.1.1
```

### Issue 3: Connection Timeouts
```bash
# Check if Central Server is running
curl localhost:5000/

# Check firewall settings
sudo ufw status

# Check service connectivity
netstat -tlnp | grep :5000
```

### Issue 4: SSL Certificate Issues
```bash
# Check certificate validity
openssl s_client -connect rpi.yourdomain.com:443

# Force SSL/TLS settings in config
echo "tls-timeout: 10s" >> ~/.cloudflared/config.yml
```

---

## 📈 Performance Optimization

### 1. **Tunnel Configuration**
```yaml
# Optimize for performance
http2-origin: true
chunked-encoding: true
compression-quality: 0
keep-alive-connections: 100
keep-alive-timeout: 90s
```

### 2. **Central Server Optimization**
```bash
# Increase Gunicorn workers
sudo nano /etc/systemd/system/central-server.service
# Change --workers 4 to --workers 8 (adjust based on RPi specs)

# Restart services
sudo systemctl daemon-reload
sudo systemctl restart central-server
```

### 3. **Monitoring**
```yaml
# Enable metrics in config.yml
metrics: 0.0.0.0:2000
```

---

## 🎉 Success Checklist

After completing all phases, you should have:

- ✅ **Cloudflare account** with your domain
- ✅ **DNS managed by Cloudflare**
- ✅ **Cloudflared installed** on RPi
- ✅ **Tunnel authenticated** and configured
- ✅ **DNS routing** to your subdomain
- ✅ **Service running** automatically
- ✅ **HTTPS access** from anywhere: `https://rpi.yourdomain.com`

### Final Test
```bash
# Test from any device, anywhere
curl https://rpi.yourdomain.com/api/stats

# Should return JSON with system statistics
```

**🎊 Congratulations! Your Central Server is now globally accessible with enterprise-grade security!**

---

## 📚 Additional Resources

- [Cloudflare Tunnel Documentation](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps)
- [Cloudflare Zero Trust](https://www.cloudflare.com/zero-trust/)
- [Raspberry Pi Performance Tuning](https://www.raspberrypi.org/documentation/configuration/)

---

## 🆘 Support

If you encounter issues:
1. Check the troubleshooting section above
2. Review Cloudflare Tunnel logs: `sudo journalctl -u cloudflared -f`
3. Verify your domain DNS settings in Cloudflare dashboard
4. Test local connectivity first: `curl localhost:5000/` 