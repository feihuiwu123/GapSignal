#!/bin/bash
# GapSignal Ubuntu Setup Script
# Run this script to set up a fresh Ubuntu server for GapSignal

set -e

echo "=========================================="
echo "GapSignal Ubuntu Setup Script"
echo "=========================================="
echo ""

# Check if running as root
if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root. Use sudo or switch to root user."
    echo "Usage: sudo $0"
    exit 1
fi

# Configuration
APP_NAME="gapsignal"
APP_DIR="/opt/$APP_NAME"

# Update system
echo "Step 1: Updating system packages..."
apt-get update
apt-get upgrade -y

# Install dependencies
echo "Step 2: Installing system dependencies..."
apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    nginx \
    supervisor \
    git \
    curl \
    wget \
    build-essential \
    python3-dev \
    ufw \
    htop \
    tmux

# Create application directory
echo "Step 3: Creating application directory..."
mkdir -p "$APP_DIR"
chown -R www-data:www-data "$APP_DIR"

# Clone or copy application code
echo "Step 4: Setting up application code..."
if [[ -d "$APP_DIR/.git" ]]; then
    echo "Git repository already exists, pulling latest changes..."
    cd "$APP_DIR"
    sudo -u www-data git pull origin main
else
    echo "Please copy your GapSignal code to $APP_DIR"
    echo "You can use:"
    echo "  scp -r /path/to/gapsignal root@your-server:/opt/"
    echo "Then run: chown -R www-data:www-data $APP_DIR"
fi

# Setup Python virtual environment
echo "Step 5: Setting up Python environment..."
cd "$APP_DIR"
sudo -u www-data python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip

if [[ -f "requirements.txt" ]]; then
    pip install -r requirements.txt
else
    echo "Warning: requirements.txt not found!"
    echo "Installing default dependencies..."
    pip install python-binance Flask pandas numpy matplotlib plotly waitress
fi

# Setup configuration
echo "Step 6: Setting up configuration..."
if [[ -f ".env.example" ]] && [[ ! -f ".env" ]]; then
    cp .env.example .env
    echo ""
    echo "IMPORTANT: Please edit $APP_DIR/.env with your Binance API keys:"
    echo "  nano $APP_DIR/.env"
    echo ""
    echo "Required settings:"
    echo "  BINANCE_API_KEY=your_api_key"
    echo "  BINANCE_API_SECRET=your_api_secret"
    echo ""
    read -p "Press Enter to continue after editing .env file..."
fi

# Setup systemd service
echo "Step 7: Setting up systemd service..."
cat > /etc/systemd/system/$APP_NAME.service << EOF
[Unit]
Description=GapSignal Trading System
After=network.target
Requires=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/venv/bin:$PATH"
ExecStart=$APP_DIR/venv/bin/python $APP_DIR/main.py
Restart=on-failure
RestartSec=10
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=$APP_NAME

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable $APP_NAME

# Setup Nginx
echo "Step 8: Setting up Nginx..."
cat > /etc/nginx/sites-available/$APP_NAME << EOF
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:6000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Static files
    location /static {
        alias $APP_DIR/app/web/static;
        expires 1d;
        add_header Cache-Control "public";
    }

    # Security headers
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
    add_header X-XSS-Protection "1; mode=block";
}
EOF

ln -sf /etc/nginx/sites-available/$APP_NAME /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true

# Test Nginx configuration
nginx -t

# Setup firewall
echo "Step 9: Configuring firewall..."
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

# Start services
echo "Step 10: Starting services..."
systemctl restart nginx
systemctl start $APP_NAME

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "GapSignal has been installed and configured."
echo ""
echo "Important information:"
echo "  Application directory: $APP_DIR"
echo "  Service name: $APP_NAME"
echo "  Web interface: http://your-server-ip"
echo "  Service status: systemctl status $APP_NAME"
echo "  View logs: journalctl -u $APP_NAME -f"
echo ""
echo "Next steps:"
echo "1. Ensure your .env file has correct API keys"
echo "2. Restart the service if you updated .env:"
echo "   systemctl restart $APP_NAME"
echo "3. Monitor logs for any issues:"
echo "   journalctl -u $APP_NAME -f"
echo ""
echo "To update the application:"
echo "  cd $APP_DIR"
echo "  sudo -u www-data git pull origin main"
echo "  $APP_DIR/venv/bin/pip install -r requirements.txt"
echo "  systemctl restart $APP_NAME"
echo ""
echo "For help, check the README.md file in $APP_DIR"
echo "=========================================="