#!/bin/bash
# Start GapSignal service

set -e

APP_NAME="gapsignal"
APP_DIR="/opt/$APP_NAME"
VENV_DIR="$APP_DIR/venv"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "Starting GapSignal service..."

# Check if running as root
if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}Error: This script must be run as root${NC}"
    echo "Use: sudo $0"
    exit 1
fi

# Check if service exists
if ! systemctl list-unit-files | grep -q "$APP_NAME.service"; then
    echo -e "${RED}Error: Service $APP_NAME not found${NC}"
    echo "Run setup_ubuntu.sh first to install the service"
    exit 1
fi

# Check if already running
if systemctl is-active --quiet "$APP_NAME"; then
    echo "Service is already running"
    echo "Restarting instead..."
    systemctl restart "$APP_NAME"
else
    # Start the service
    systemctl start "$APP_NAME"
fi

# Wait a moment for service to start
sleep 2

# Check status
if systemctl is-active --quiet "$APP_NAME"; then
    echo -e "${GREEN}Service started successfully${NC}"
    echo ""
    echo "Service status:"
    systemctl status "$APP_NAME" --no-pager

    echo ""
    echo "Web interface: http://localhost:6000"
    echo "Or via Nginx: http://your-server-ip"
    echo ""
    echo "To view logs: journalctl -u $APP_NAME -f"
else
    echo -e "${RED}Failed to start service${NC}"
    echo "Check logs with: journalctl -u $APP_NAME"
    exit 1
fi