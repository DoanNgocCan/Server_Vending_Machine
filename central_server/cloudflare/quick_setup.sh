#!/bin/bash

# Quick Cloudflare Tunnel Setup Script
# This script provides a simplified setup process for experienced users

set -e

echo "🚀 Quick Cloudflare Tunnel Setup"
echo "================================="
echo

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "❌ Please run as regular user (not root)"
    exit 1
fi

# Check if Central Server is running
if ! curl -s localhost:5000/ > /dev/null; then
    echo "❌ Central Server is not running on port 5000"
    echo "   Please start your Central Server first:"
    echo "   cd /path/to/central_server && python app.py"
    exit 1
fi

echo "✅ Central Server is running on port 5000"
echo

# Get domain information
read -p "Enter your domain (e.g., example.com): " DOMAIN
read -p "Enter subdomain (e.g., rpi): " SUBDOMAIN

FULL_DOMAIN="${SUBDOMAIN}.${DOMAIN}"
TUNNEL_NAME="rpi-central"

echo
echo "📋 Configuration Summary:"
echo "   Domain: $DOMAIN"
echo "   Subdomain: $SUBDOMAIN"  
echo "   Full URL: https://$FULL_DOMAIN"
echo "   Tunnel Name: $TUNNEL_NAME"
echo

read -p "Continue with setup? (y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Setup cancelled"
    exit 1
fi

# Install cloudflared if not exists
if ! command -v cloudflared &> /dev/null; then
    echo "📦 Installing cloudflared..."
    
    ARCH=$(uname -m)
    case $ARCH in
        x86_64) ARCH="amd64" ;;
        aarch64) ARCH="arm64" ;;
        armv7l) ARCH="arm" ;;
        *) echo "❌ Unsupported architecture: $ARCH"; exit 1 ;;
    esac
    
    wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-${ARCH}
    chmod +x cloudflared-linux-${ARCH}
    sudo mv cloudflared-linux-${ARCH} /usr/local/bin/cloudflared
    
    echo "✅ cloudflared installed"
else
    echo "✅ cloudflared already installed"
fi

# Check authentication
if [ ! -f ~/.cloudflared/cert.pem ]; then
    echo "🔐 Authentication required"
    echo "   A browser window will open for authentication"
    echo "   1. Login to Cloudflare"
    echo "   2. Select domain: $DOMAIN"
    echo "   3. Click 'Authorize'"
    echo
    read -p "Press Enter to continue..."
    
    cloudflared tunnel login
    
    if [ ! -f ~/.cloudflared/cert.pem ]; then
        echo "❌ Authentication failed"
        exit 1
    fi
    
    echo "✅ Authentication successful"
else
    echo "✅ Already authenticated"
fi

# Create tunnel
echo "🛠️ Creating tunnel..."
if cloudflared tunnel list 2>/dev/null | grep -q "$TUNNEL_NAME"; then
    echo "✅ Tunnel '$TUNNEL_NAME' already exists"
    TUNNEL_ID=$(cloudflared tunnel list | grep "$TUNNEL_NAME" | awk '{print $1}')
else
    cloudflared tunnel create "$TUNNEL_NAME"
    TUNNEL_ID=$(cloudflared tunnel list | grep "$TUNNEL_NAME" | awk '{print $1}')
    echo "✅ Tunnel created: $TUNNEL_NAME"
fi

# Create configuration
echo "📝 Creating configuration..."
mkdir -p ~/.cloudflared

cat > ~/.cloudflared/config.yml << EOF
tunnel: $TUNNEL_ID
credentials-file: /home/pi/.cloudflared/$TUNNEL_ID.json

ingress:
  - hostname: $FULL_DOMAIN
    service: http://localhost:5000
  - service: http_status:404

# Performance optimizations
http2-origin: true
chunked-encoding: true
compression-quality: 0
keep-alive-connections: 100
keep-alive-timeout: 90s
EOF

echo "✅ Configuration created"

# Configure DNS
echo "🌐 Configuring DNS..."
cloudflared tunnel route dns "$TUNNEL_NAME" "$FULL_DOMAIN"
echo "✅ DNS configured"

# Install as service
echo "⚙️ Installing as service..."
sudo cloudflared service install --config=/home/pi/.cloudflared/config.yml
sudo systemctl enable cloudflared
sudo systemctl start cloudflared

# Wait for service to start
echo "⏳ Waiting for service to start..."
sleep 5

# Check service status
if systemctl is-active --quiet cloudflared; then
    echo "✅ Service is running"
else
    echo "❌ Service failed to start"
    sudo systemctl status cloudflared
    exit 1
fi

# Test connectivity
echo "🧪 Testing connectivity..."
sleep 5

if curl -s -f "https://$FULL_DOMAIN/" > /dev/null; then
    echo "✅ Tunnel is working!"
else
    echo "⚠️ Tunnel may not be ready yet (DNS propagation takes time)"
fi

# Create management script
echo "📜 Creating management script..."
cat > ~/tunnel_control.sh << EOF
#!/bin/bash
case "\$1" in
    start)   sudo systemctl start cloudflared; echo "Tunnel started" ;;
    stop)    sudo systemctl stop cloudflared; echo "Tunnel stopped" ;;
    restart) sudo systemctl restart cloudflared; echo "Tunnel restarted" ;;
    status)  sudo systemctl status cloudflared ;;
    logs)    sudo journalctl -u cloudflared -f ;;
    test)    curl -s "https://$FULL_DOMAIN/" && echo "✅ Working" || echo "❌ Not responding" ;;
    url)     echo "https://$FULL_DOMAIN/" ;;
    *) echo "Usage: \$0 {start|stop|restart|status|logs|test|url}" ;;
esac
EOF

chmod +x ~/tunnel_control.sh

# Create symbolic link
mkdir -p ~/bin
ln -sf ~/tunnel_control.sh ~/bin/tunnel

echo
echo "🎉 Setup Complete!"
echo "=================="
echo
echo "Your Central Server is now accessible at:"
echo "🌐 https://$FULL_DOMAIN"
echo
echo "Available endpoints:"
echo "• Health check: https://$FULL_DOMAIN/"
echo "• Device registration: https://$FULL_DOMAIN/api/devices"
echo "• Send data: https://$FULL_DOMAIN/api/device/data"
echo "• System stats: https://$FULL_DOMAIN/api/stats"
echo
echo "Management commands:"
echo "• ~/bin/tunnel status    - Check tunnel status"
echo "• ~/bin/tunnel logs      - View tunnel logs"
echo "• ~/bin/tunnel test      - Test connectivity"
echo "• ~/bin/tunnel url       - Show tunnel URL"
echo
echo "Note: DNS propagation may take a few minutes."
echo "Test with: curl https://$FULL_DOMAIN/"
echo 