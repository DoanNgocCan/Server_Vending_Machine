#!/bin/bash

# Script to setup systemd services for Central Server and Dashboard

PROJECT_DIR="/home/pi/Desktop/SERVER/icc-25-cdpd-uit/central_server"
VENV_DIR="$PROJECT_DIR/venv"

echo "=== Setting up Services ==="

# 1. Install Dashboard Dependencies
echo "Installing Dashboard dependencies..."
if [ -d "$VENV_DIR" ]; then
    source "$VENV_DIR/bin/activate"
    pip install streamlit plotly pandas
else
    echo "Error: Virtual environment not found at $VENV_DIR"
    echo "Please run deploy.sh first to create the environment."
    exit 1
fi

# 2. Setup Central Server Service
echo "Setting up Central Server Service..."
sudo cp "$PROJECT_DIR/central-server.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable central-server.service
sudo systemctl restart central-server.service

# 3. Setup Dashboard Service
echo "Setting up Dashboard Service..."
sudo cp "$PROJECT_DIR/dashboard/dashboard.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable dashboard.service
sudo systemctl restart dashboard.service

echo "=== Setup Complete ==="
echo "Check status with:"
echo "  sudo systemctl status central-server.service"
echo "  sudo systemctl status dashboard.service"
