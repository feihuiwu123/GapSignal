#!/bin/bash
# Stop GapSignal service

set -e

APP_NAME="gapsignal"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "Stopping GapSignal service..."

# Check if running as root
if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}Error: This script must be run as root${NC}"
    echo "Use: sudo $0"
    exit 1
fi

# Check if service exists
if ! systemctl list-unit-files | grep -q "$APP_NAME.service"; then
    echo -e "${RED}Error: Service $APP_NAME not found${NC}"
    echo "Service may not be installed"
    exit 1
fi

# Check if already stopped
if ! systemctl is-active --quiet "$APP_NAME"; then
    echo "Service is already stopped"
    exit 0
fi

# Stop the service
systemctl stop "$APP_NAME"

# Wait a moment
sleep 1

# Check status
if ! systemctl is-active --quiet "$APP_NAME"; then
    echo -e "${GREEN}Service stopped successfully${NC}"
    echo ""
    echo "To start again: sudo systemctl start $APP_NAME"
else
    echo -e "${RED}Failed to stop service${NC}"
    echo "Try forcing stop: sudo systemctl kill $APP_NAME"
    exit 1
fi