#!/bin/bash

# Cloudflare Tunnel Setup Script
# This script installs and configures Cloudflare Tunnel for Central Server

set -e  # Exit on any error

# Configuration
TUNNEL_NAME="rpi-central"
DOMAIN=""  # Will be set by user
SUBDOMAIN=""  # Will be set by user
SERVICE_PORT="5000"
CONFIG_DIR="/home/pi/.cloudflared"
LOG_FILE="/var/log/cloudflare_tunnel_setup.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to log messages
log_message() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] SUCCESS:${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1" | tee -a "$LOG_FILE"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to get user input
get_user_input() {
    echo -e "${BLUE}=== Cloudflare Tunnel Configuration ===${NC}"
    echo "Please provide the following information:"
    echo
    
    while [ -z "$DOMAIN" ]; do
        read -p "Enter your domain (e.g., example.com): " DOMAIN
        if [ -z "$DOMAIN" ]; then
            log_error "Domain cannot be empty!"
        fi
    done
    
    while [ -z "$SUBDOMAIN" ]; do
        read -p "Enter subdomain for your RPi (e.g., rpi): " SUBDOMAIN
        if [ -z "$SUBDOMAIN" ]; then
            log_error "Subdomain cannot be empty!"
        fi
    done
    
    FULL_DOMAIN="${SUBDOMAIN}.${DOMAIN}"
    
    echo
    log_message "Configuration:"
    log_message "  Domain: $DOMAIN"
    log_message "  Subdomain: $SUBDOMAIN"
    log_message "  Full URL: https://$FULL_DOMAIN"
    log_message "  Local Service: http://localhost:$SERVICE_PORT"
    echo
    
    read -p "Is this correct? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_error "Setup cancelled by user"
        exit 1
    fi
}

# Function to install cloudflared
install_cloudflared() {
    log_message "Installing Cloudflare Tunnel CLI..."
    
    # Check if already installed
    if command_exists cloudflared; then
        log_warning "cloudflared already installed"
        cloudflared --version
        return 0
    fi
    
    # Determine architecture
    ARCH=$(uname -m)
    case $ARCH in
        x86_64)
            ARCH="amd64"
            ;;
        aarch64)
            ARCH="arm64"
            ;;
        armv7l)
            ARCH="arm"
            ;;
        *)
            log_error "Unsupported architecture: $ARCH"
            exit 1
            ;;
    esac
    
    # Download and install
    DOWNLOAD_URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-${ARCH}"
    
    log_message "Downloading cloudflared for $ARCH..."
    wget -O /tmp/cloudflared "$DOWNLOAD_URL"
    
    # Make executable and move to PATH
    chmod +x /tmp/cloudflared
    sudo mv /tmp/cloudflared /usr/local/bin/cloudflared
    
    # Verify installation
    if command_exists cloudflared; then
        log_success "cloudflared installed successfully"
        cloudflared --version
    else
        log_error "Failed to install cloudflared"
        exit 1
    fi
}

# Function to authenticate with Cloudflare
authenticate_cloudflare() {
    log_message "Authenticating with Cloudflare..."
    
    # Check if already authenticated
    if [ -f "$CONFIG_DIR/cert.pem" ]; then
        log_warning "Already authenticated (cert.pem exists)"
        return 0
    fi
    
    log_message "Opening browser for authentication..."
    log_message "Please follow these steps:"
    log_message "1. A browser window will open"
    log_message "2. Login to your Cloudflare account"
    log_message "3. Select your domain: $DOMAIN"
    log_message "4. Click 'Authorize'"
    echo
    
    read -p "Press Enter to continue..."
    
    # Run authentication
    cloudflared tunnel login
    
    # Verify authentication
    if [ -f "$CONFIG_DIR/cert.pem" ]; then
        log_success "Authentication successful"
    else
        log_error "Authentication failed"
        exit 1
    fi
}

# Function to create tunnel
create_tunnel() {
    log_message "Creating Cloudflare Tunnel..."
    
    # Check if tunnel already exists
    if cloudflared tunnel list | grep -q "$TUNNEL_NAME"; then
        log_warning "Tunnel '$TUNNEL_NAME' already exists"
        TUNNEL_ID=$(cloudflared tunnel list | grep "$TUNNEL_NAME" | awk '{print $1}')
    else
        # Create new tunnel
        cloudflared tunnel create "$TUNNEL_NAME"
        TUNNEL_ID=$(cloudflared tunnel list | grep "$TUNNEL_NAME" | awk '{print $1}')
        log_success "Tunnel created: $TUNNEL_NAME ($TUNNEL_ID)"
    fi
    
    # Export tunnel ID for other functions
    export TUNNEL_ID
}

# Function to create tunnel configuration
create_tunnel_config() {
    log_message "Creating tunnel configuration..."
    
    # Create config directory if it doesn't exist
    mkdir -p "$CONFIG_DIR"
    
    # Create configuration file
    cat > "$CONFIG_DIR/config.yml" << EOF
tunnel: $TUNNEL_ID
credentials-file: $CONFIG_DIR/$TUNNEL_ID.json

ingress:
  - hostname: $FULL_DOMAIN
    service: http://localhost:$SERVICE_PORT
  - service: http_status:404

# Optional: Enable additional features
# metrics: 0.0.0.0:2000
# warp-routing:
#   enabled: true
EOF
    
    log_success "Configuration created: $CONFIG_DIR/config.yml"
}

# Function to configure DNS
configure_dns() {
    log_message "Configuring DNS..."
    
    # Add DNS record
    cloudflared tunnel route dns "$TUNNEL_NAME" "$FULL_DOMAIN"
    
    log_success "DNS configured: $FULL_DOMAIN → $TUNNEL_NAME"
}

# Function to install as service
install_service() {
    log_message "Installing tunnel as system service..."
    # Phát hiện xem subcommand 'service install' có hỗ trợ --config không
    if cloudflared service install --help 2>&1 | grep -q "--config"; then
        log_message "Detected legacy style 'cloudflared service install' supporting --config"
        sudo cloudflared service install --config="$CONFIG_DIR/config.yml" || log_warning "cloudflared service install returned non-zero, sẽ thử fallback thủ công"
    else
        log_message "'cloudflared service install' không hỗ trợ --config (phiên bản mới) -> tạo systemd unit thủ công"
    fi

    # Kiểm tra đã tạo unit chưa
    if ! systemctl list-unit-files | grep -q '^cloudflared.service'; then
        log_message "Creating /etc/systemd/system/cloudflared.service manually..."
        SERVICE_FILE="/etc/systemd/system/cloudflared.service"
        sudo bash -c "cat > $SERVICE_FILE" << EOF
[Unit]
Description=Cloudflare Tunnel: $TUNNEL_NAME
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=$USER
ExecStart=/usr/local/bin/cloudflared --no-autoupdate --config $CONFIG_DIR/config.yml tunnel run $TUNNEL_NAME
Restart=on-failure
RestartSec=5
LimitNOFILE=1048576

[Install]
WantedBy=multi-user.target
EOF
        sudo systemctl daemon-reload
    fi

    # Enable & start
    sudo systemctl enable cloudflared || true
    sudo systemctl restart cloudflared || sudo systemctl start cloudflared || true

    # Verify
    if systemctl is-active --quiet cloudflared; then
        log_success "Cloudflare Tunnel service is running"
    else
        log_error "Failed to start Cloudflare Tunnel service (kiểm tra log: sudo journalctl -u cloudflared -xe)"
        exit 1
    fi
}

# Function to test tunnel
test_tunnel() {
    log_message "Testing tunnel connectivity..."
    
    # Wait for tunnel to be ready
    sleep 10
    
    # Test health endpoint
    if curl -s -f "https://$FULL_DOMAIN/" > /dev/null; then
        log_success "Tunnel is working! Your Central Server is accessible at:"
        echo -e "${GREEN}https://$FULL_DOMAIN/${NC}"
    else
        log_warning "Tunnel may not be ready yet. Please check:"
        echo "  1. Central Server is running on port $SERVICE_PORT"
        echo "  2. DNS has propagated (may take a few minutes)"
        echo "  3. Cloudflare Tunnel service is active"
        echo
        echo "Test manually with: curl https://$FULL_DOMAIN/"
    fi
}

# Function to create management scripts
create_management_scripts() {
    log_message "Creating tunnel management scripts..."
    
    # Create tunnel control script
    cat > "$CONFIG_DIR/tunnel_control.sh" << 'EOF'
#!/bin/bash

# Cloudflare Tunnel Control Script

case "$1" in
    start)
        sudo systemctl start cloudflared
        echo "Tunnel started"
        ;;
    stop)
        sudo systemctl stop cloudflared
        echo "Tunnel stopped"
        ;;
    restart)
        sudo systemctl restart cloudflared
        echo "Tunnel restarted"
        ;;
    status)
        sudo systemctl status cloudflared
        ;;
    logs)
        sudo journalctl -u cloudflared -f
        ;;
    test)
        curl -s -f "https://FULL_DOMAIN_PLACEHOLDER/" && echo "Tunnel is working" || echo "Tunnel is not responding"
        ;;
    config)
        nano ~/.cloudflared/config.yml
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs|test|config}"
        exit 1
        ;;
esac
EOF
    
    # Replace placeholder with actual domain
    sed -i "s/FULL_DOMAIN_PLACEHOLDER/$FULL_DOMAIN/g" "$CONFIG_DIR/tunnel_control.sh"
    
    chmod +x "$CONFIG_DIR/tunnel_control.sh"
    
    # Create symbolic link in user's bin
    mkdir -p "$HOME/bin"
    ln -sf "$CONFIG_DIR/tunnel_control.sh" "$HOME/bin/tunnel"
    
    log_success "Management scripts created"
    log_message "Usage: ~/bin/tunnel {start|stop|restart|status|logs|test|config}"
}

# Function to display final information
display_final_info() {
    echo
    echo -e "${GREEN}=== Cloudflare Tunnel Setup Complete ===${NC}"
    echo
    echo "Your Central Server is now accessible at:"
    echo -e "${GREEN}https://$FULL_DOMAIN${NC}"
    echo
    echo "Available endpoints:"
    echo "  • Health check: https://$FULL_DOMAIN/"
    echo "  • API docs: https://$FULL_DOMAIN/api/"
    echo "  • Device registration: https://$FULL_DOMAIN/api/devices"
    echo "  • Data endpoint: https://$FULL_DOMAIN/api/device/data"
    echo
    echo "Management commands:"
    echo "  • ~/bin/tunnel status    - Check tunnel status"
    echo "  • ~/bin/tunnel logs      - View tunnel logs"
    echo "  • ~/bin/tunnel restart   - Restart tunnel"
    echo "  • ~/bin/tunnel test      - Test connectivity"
    echo
    echo "Configuration files:"
    echo "  • Config: $CONFIG_DIR/config.yml"
    echo "  • Credentials: $CONFIG_DIR/$TUNNEL_ID.json"
    echo "  • Certificate: $CONFIG_DIR/cert.pem"
    echo
}

# Main function
main() {
    echo -e "${BLUE}=== Cloudflare Tunnel Setup for Central Server ===${NC}"
    echo
    
    # Check if running as root
    if [ "$EUID" -eq 0 ]; then
        log_error "Please run this script as a regular user (not root)"
        exit 1
    fi
    
    # Create log file
    sudo touch "$LOG_FILE"
    sudo chown "$USER:$USER" "$LOG_FILE"
    
    log_message "Starting Cloudflare Tunnel setup..."
    
    # Get user configuration
    get_user_input
    
    # Install cloudflared
    install_cloudflared
    
    # Authenticate
    authenticate_cloudflare
    
    # Create tunnel
    create_tunnel
    
    # Create configuration
    create_tunnel_config
    
    # Configure DNS
    configure_dns
    
    # Install as service
    install_service
    
    # Create management scripts
    create_management_scripts
    
    # Test tunnel
    test_tunnel
    
    # Display final information
    display_final_info
    
    log_success "Cloudflare Tunnel setup completed successfully!"
}

# Handle script arguments
case "${1:-setup}" in
    setup)
        main
        ;;
    install)
        install_cloudflared
        ;;
    auth)
        authenticate_cloudflare
        ;;
    create)
        create_tunnel
        ;;
    config)
        create_tunnel_config
        ;;
    dns)
        configure_dns
        ;;
    service)
        install_service
        ;;
    test)
        test_tunnel
        ;;
    *)
        echo "Usage: $0 {setup|install|auth|create|config|dns|service|test}"
        echo "  setup   - Full setup process (default)"
        echo "  install - Install cloudflared only"
        echo "  auth    - Authenticate with Cloudflare"
        echo "  create  - Create tunnel"
        echo "  config  - Create configuration"
        echo "  dns     - Configure DNS"
        echo "  service - Install as service"
        echo "  test    - Test tunnel"
        exit 1
        ;;
esac 