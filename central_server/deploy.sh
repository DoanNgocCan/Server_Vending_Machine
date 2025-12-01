#!/bin/bash

# Central Server Deployment Script
# This script handles the deployment of the central server application

set -e  # Exit on any error

echo "=== Central Server Deployment Started ==="
echo "Timestamp: $(date)"

# Configuration (có thể override bằng biến môi trường)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$SCRIPT_DIR}"
SERVICE_NAME="${SERVICE_NAME:-central-server}"
BACKUP_DIR="${BACKUP_DIR:-/home/pi/backups}"
LOG_FILE="${LOG_FILE:-/var/log/central_server_deploy.log}"
FALLBACK_LOG_DIR="$HOME/central_server_logs"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Init log file with fallback if /var/log not writable
init_log() {
    if touch "$LOG_FILE" 2>/dev/null; then
        return
    fi
    if sudo sh -c "touch '$LOG_FILE' && chown $USER:$USER '$LOG_FILE'" 2>/dev/null; then
        return
    fi
    mkdir -p "$FALLBACK_LOG_DIR"
    LOG_FILE="$FALLBACK_LOG_DIR/central_server_deploy.log"
    touch "$LOG_FILE"
    echo "[INFO] Fallback log file: $LOG_FILE" >&2
}
init_log

# Function to log messages
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}
log_warning() { log_message "WARNING: $1"; }
log_error() { log_message "ERROR: $1"; }

# Function to create backup
create_backup() {
    log_message "Creating backup..."
    BACKUP_NAME="central_server_backup_$(date +%Y%m%d_%H%M%S).tar.gz"
    tar --exclude='venv' --exclude='__pycache__' --exclude='*.pyc' -czf "$BACKUP_DIR/$BACKUP_NAME" -C "$PROJECT_DIR" .
    log_message "Backup created: $BACKUP_DIR/$BACKUP_NAME"
}

# Function to update code from git
update_code() {
    log_message "Updating code from git repository..."
    cd "$PROJECT_DIR"
    
    # Check if git repository exists
    if [ -d ".git" ]; then
        git fetch origin
        git reset --hard origin/main
        log_message "Code updated from git repository"
    else
        log_message "Warning: Not a git repository. Skipping git update."
    fi
}

# Function to install dependencies
install_dependencies() {
    log_message "Installing/updating dependencies..."
    cd "$PROJECT_DIR"
    log_message "Project directory: $PROJECT_DIR"
    python3 -m venv venv
    # Activate virtual environment
    source venv/bin/activate
    
    # Install requirements
    pip install -r requirements.txt
    
    log_message "Dependencies installed/updated"
}

# Function to run database migrations
migrate_database() {
    log_message "Running database migrations..."
    cd "$PROJECT_DIR"
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Initialize database (will create tables if they don't exist)
    python -c "from db.db import db_handler; print('Database initialized')"
    
    log_message "Database migrations completed"
}

# Function to restart service
restart_service() {
    log_message "Restarting service..."
    
    # Check if service exists
    if systemctl is-enabled "$SERVICE_NAME" >/dev/null 2>&1; then
        systemctl restart "$SERVICE_NAME"
        sleep 5
        
        # Check if service is running
        if systemctl is-active "$SERVICE_NAME" >/dev/null 2>&1; then
            log_message "Service restarted successfully"
        else
            log_message "ERROR: Service failed to start"
            systemctl status "$SERVICE_NAME"
            exit 1
        fi
    else
        log_message "Warning: Service $SERVICE_NAME not found. Starting manually..."
        cd "$PROJECT_DIR"
        source venv/bin/activate
        nohup gunicorn --bind 0.0.0.0:5000 --workers 4 app:app > /var/log/central_server.log 2>&1 &
        log_message "Application started manually"
    fi
}

# Function to verify deployment
verify_deployment() {
    log_message "Verifying deployment..."
    
    # Wait for service to be ready
    sleep 10
    
    # Test health endpoint
    if curl -s -f http://localhost:5000/ > /dev/null; then
        log_message "Health check passed - deployment successful"
    else
        log_message "ERROR: Health check failed"
        exit 1
    fi
}

# Function to cleanup old backups
cleanup_backups() {
    log_message "Cleaning up old backups..."
    
    # Keep only last 10 backups
    cd "$BACKUP_DIR"
    ls -t central_server_backup_*.tar.gz | tail -n +11 | xargs -r rm
    
    log_message "Backup cleanup completed"
}

# Main deployment process
main() {
    log_message "Starting deployment process..."
    
    # Check if running as root for systemd operations
    if [ "$EUID" -ne 0 ]; then
        log_message "Note: Not running as root. Some operations may require sudo."
    fi
    
    # Create backup
    create_backup
    
    # Update code
    update_code
    
    # Install dependencies
    install_dependencies
    
    # Migrate database
    migrate_database
    
    # Restart service
    restart_service
    
    # Verify deployment
    verify_deployment
    
    # Cleanup old backups
    cleanup_backups
    
    log_message "Deployment completed successfully!"
    echo "=== Central Server Deployment Completed ==="
}

# Handle script arguments
case "${1:-deploy}" in
    deploy)
        main
        ;;
    backup)
        create_backup
        ;;
    restart)
        restart_service
        ;;
    verify)
        verify_deployment
        ;;
    cleanup)
        cleanup_backups
        ;;
    *)
        echo "Usage: $0 {deploy|backup|restart|verify|cleanup}"
        echo "  deploy  - Full deployment process (default)"
        echo "  backup  - Create backup only"
        echo "  restart - Restart service only"
        echo "  verify  - Verify deployment only"
        echo "  cleanup - Cleanup old backups only"
        exit 1
        ;;
esac