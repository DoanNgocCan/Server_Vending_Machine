# Central Server Installation Guide

## 📋 Prerequisites

### Hardware Requirements
- Raspberry Pi 4B (4GB RAM recommended)
- MicroSD card (32GB minimum)
- Network connectivity (WiFi or Ethernet)

### Software Requirements  
- Raspberry Pi OS Lite (recommended)
- Python 3.8 or higher
- Git

## 🚀 Installation Steps

### 1. Prepare Raspberry Pi

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y python3-pip python3-venv git curl

# Create project directory
sudo mkdir -p /home/pi/central_server
sudo chown pi:pi /home/pi/central_server
cd /home/pi/central_server
```

### 2. Clone and Setup Project

```bash
# Clone repository
git clone <your-repo-url> .

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Initialize Database

```bash
# The database will be automatically initialized when the app starts
# You can also manually initialize it:
python -c "from db.db import db_handler; print('Database initialized')"
```

### 4. Configure Environment

```bash
# Create environment file (optional)
cat > .env << EOF
FLASK_ENV=production
FLASK_DEBUG=False
DATABASE_PATH=/home/pi/central_server/central_server.db
LOG_LEVEL=INFO
EOF
```

### 5. Setup SystemD Service

```bash
# Copy service file
sudo cp services/flask.service /etc/systemd/system/central-server.service

# Edit service file if needed (adjust paths)
sudo nano /etc/systemd/system/central-server.service

# Reload systemd and enable service
sudo systemctl daemon-reload
sudo systemctl enable central-server.service
sudo systemctl start central-server.service

# Check service status
sudo systemctl status central-server.service
```

### 6. Configure Firewall (Optional)

```bash
# Install UFW if not installed
sudo apt install -y ufw

# Allow SSH
sudo ufw allow ssh

# Allow HTTP on port 5000
sudo ufw allow 5000/tcp

# Enable firewall
sudo ufw enable
```

### 7. Setup Deployment Script

```bash
# Make deploy script executable
chmod +x deploy.sh

# Create log directory
sudo mkdir -p /var/log
sudo touch /var/log/central_server_deploy.log
sudo chown pi:pi /var/log/central_server_deploy.log

# Test deployment
./deploy.sh
```

## 🔧 Configuration

### Database Location
- Default: `/home/pi/central_server/central_server.db`
- Can be changed in `db/db.py`

### Service Configuration
- Service name: `central-server`
- Port: `5000`
- Workers: `4` (adjust based on your Pi's specs)

### Logging
- Application logs: `/var/log/central_server.log`
- Deployment logs: `/var/log/central_server_deploy.log`

## 🧪 Testing

### 1. Test API Endpoints

```bash
# Health check
curl http://localhost:5000/

# Register a device
curl -X POST http://localhost:5000/api/devices \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "test-device",
    "device_name": "Test Device",
    "device_type": "sensor",
    "description": "Test sensor device"
  }'

# Send test data
curl -X POST http://localhost:5000/api/device/data \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "test-device",
    "type": "sensor",
    "payload": {
      "temp": 25.5,
      "humidity": 60
    }
  }'

# Get device data
curl http://localhost:5000/api/device/test-device/data
```

### 2. Test Service Management

```bash
# Restart service
sudo systemctl restart central-server

# Check service logs
sudo journalctl -u central-server -f

# Check service status
sudo systemctl status central-server
```

## 🔄 Deployment & Updates

### Manual Deployment

```bash
# Run deployment script
./deploy.sh

# Or specific operations
./deploy.sh backup    # Create backup only
./deploy.sh restart   # Restart service only
./deploy.sh verify    # Verify deployment
```

### Automated Deployment via Webhook

1. Setup webhook endpoint in your Flask app
2. Configure your Git repository to send webhooks
3. Webhook will trigger automatic deployment

### Backup & Recovery

```bash
# Backups are automatically created in /home/pi/backups
# Manual backup
./deploy.sh backup

# Restore from backup
cd /home/pi/backups
tar -xzf central_server_backup_YYYYMMDD_HHMMSS.tar.gz
# Copy files back to project directory
```

## 📊 Monitoring

### Check System Status

```bash
# Service status
sudo systemctl status central-server

# Resource usage
htop
df -h
free -h

# Network connections
netstat -tlnp | grep :5000
```

### View Logs

```bash
# Application logs
sudo journalctl -u central-server -f

# System logs
tail -f /var/log/syslog

# Deployment logs
tail -f /var/log/central_server_deploy.log
```

## 🔧 Troubleshooting

### Common Issues

1. **Service won't start**
   - Check service file paths
   - Verify Python virtual environment
   - Check database permissions

2. **Database errors**
   - Ensure database directory exists
   - Check file permissions
   - Verify SQLite installation

3. **Network issues**
   - Check firewall settings
   - Verify port availability
   - Check network connectivity

### Debug Commands

```bash
# Test Python environment
source venv/bin/activate
python -c "import flask; print('Flask OK')"

# Test database connection
python -c "from db.db import db_handler; print('Database OK')"

# Manual app start (debugging)
source venv/bin/activate
export FLASK_ENV=development
python app.py
```

## 📈 Performance Optimization

### For Production

1. **Increase workers** in systemd service
2. **Add Nginx reverse proxy** for better performance
3. **Setup log rotation** to prevent disk space issues
4. **Configure database optimization**

### Nginx Configuration (Optional)

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

## 🔐 Security Considerations

1. **Change default ports** if needed
2. **Setup proper firewall rules**
3. **Use HTTPS** in production
4. **Implement authentication** for sensitive endpoints
5. **Regular security updates**

## 📞 Support

If you encounter issues:
1. Check the logs
2. Review this installation guide
3. Verify all prerequisites are met
4. Check the troubleshooting section 