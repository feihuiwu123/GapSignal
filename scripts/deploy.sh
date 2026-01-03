#!/bin/bash
# GapSignal Deployment Script for Ubuntu
# Usage: ./scripts/deploy.sh [install|update|start|stop|restart|status]

set -e

# Configuration
APP_NAME="gapsignal"
APP_USER="www-data"
APP_GROUP="www-data"
APP_DIR="/opt/$APP_NAME"
VENV_DIR="$APP_DIR/venv"
LOG_DIR="/var/log/$APP_NAME"
CONFIG_DIR="/etc/$APP_NAME"
SERVICE_FILE="/etc/systemd/system/$APP_NAME.service"
NGINX_CONF="/etc/nginx/sites-available/$APP_NAME"
NGINX_ENABLED="/etc/nginx/sites-enabled/$APP_NAME"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[*]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[+]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[-]${NC} $1"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_error "This script must be run as root"
        exit 1
    fi
}

install_dependencies() {
    print_status "Installing system dependencies..."
    apt-get update
    apt-get install -y \
        python3 \
        python3-pip \
        python3-venv \
        nginx \
        supervisor \
        git \
        curl \
        build-essential \
        python3-dev
    print_success "Dependencies installed"
}

setup_directories() {
    print_status "Setting up directories..."

    # Create directories
    mkdir -p "$APP_DIR"
    mkdir -p "$LOG_DIR"
    mkdir -p "$CONFIG_DIR"

    # Set permissions
    chown -R $APP_USER:$APP_GROUP "$APP_DIR"
    chown -R $APP_USER:$APP_GROUP "$LOG_DIR"
    chown -R $APP_USER:$APP_GROUP "$CONFIG_DIR"

    chmod 755 "$APP_DIR"
    chmod 755 "$LOG_DIR"

    print_success "Directories created"
}

setup_python_environment() {
    print_status "Setting up Python virtual environment..."

    # Create virtual environment
    sudo -u $APP_USER python3 -m venv "$VENV_DIR"

    # Activate virtual environment and install dependencies
    source "$VENV_DIR/bin/activate"
    pip install --upgrade pip
    pip install -r "$APP_DIR/requirements.txt"

    print_success "Python environment setup complete"
}

setup_application() {
    print_status "Setting up application..."

    # Copy configuration files
    if [[ -f "$APP_DIR/.env.example" ]]; then
        if [[ ! -f "$APP_DIR/.env" ]]; then
            cp "$APP_DIR/.env.example" "$APP_DIR/.env"
            print_warning "Please edit $APP_DIR/.env with your API keys"
        fi
    fi

    if [[ -f "$APP_DIR/config.json" ]]; then
        cp "$APP_DIR/config.json" "$CONFIG_DIR/config.json"
    fi

    print_success "Application setup complete"
}

setup_systemd_service() {
    print_status "Setting up systemd service..."

    cat > "$SERVICE_FILE" << EOF
[Unit]
Description=GapSignal Trading System
After=network.target
Requires=network.target

[Service]
Type=simple
User=$APP_USER
Group=$APP_GROUP
WorkingDirectory=$APP_DIR
Environment="PATH=$VENV_DIR/bin:$PATH"
ExecStart=$VENV_DIR/bin/python $APP_DIR/main.py
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
    print_success "Systemd service configured"
}

setup_nginx() {
    print_status "Setting up Nginx reverse proxy..."

    # Create Nginx configuration
    cat > "$NGINX_CONF" << EOF
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:6000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        # WebSocket support (if needed in future)
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Static files (if any)
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

    # Enable site
    ln -sf "$NGINX_CONF" "$NGINX_ENABLED"

    # Test Nginx configuration
    nginx -t

    # Restart Nginx
    systemctl restart nginx

    print_success "Nginx configured"
}

setup_firewall() {
    print_status "Configuring firewall..."

    # Allow SSH
    ufw allow 22/tcp

    # Allow HTTP/HTTPS
    ufw allow 80/tcp
    ufw allow 443/tcp

    # Enable firewall
    ufw --force enable

    print_success "Firewall configured"
}

deploy_application() {
    print_status "Deploying application..."

    # Stop service if running
    systemctl stop $APP_NAME 2>/dev/null || true

    # Pull latest code (if using git)
    if [[ -d "$APP_DIR/.git" ]]; then
        cd "$APP_DIR"
        sudo -u $APP_USER git pull origin main
    fi

    # Install/update dependencies
    source "$VENV_DIR/bin/activate"
    pip install -r "$APP_DIR/requirements.txt"

    # Start service
    systemctl start $APP_NAME

    print_success "Application deployed"
}

start_service() {
    print_status "Starting $APP_NAME service..."
    systemctl start $APP_NAME
    systemctl status $APP_NAME --no-pager
    print_success "Service started"
}

stop_service() {
    print_status "Stopping $APP_NAME service..."
    systemctl stop $APP_NAME
    print_success "Service stopped"
}

restart_service() {
    print_status "Restarting $APP_NAME service..."
    systemctl restart $APP_NAME
    systemctl status $APP_NAME --no-pager
    print_success "Service restarted"
}

show_status() {
    print_status "System status:"
    echo "Service: $(systemctl is-active $APP_NAME 2>/dev/null || echo 'not installed')"
    echo "Nginx: $(systemctl is-active nginx 2>/dev/null || echo 'not installed')"
    echo "Application directory: $APP_DIR"
    echo "Log directory: $LOG_DIR"
    echo ""
    echo "Recent logs:"
    journalctl -u $APP_NAME -n 20 --no-pager || true
}

show_usage() {
    echo "Usage: $0 [install|update|start|stop|restart|status]"
    echo ""
    echo "Commands:"
    echo "  install   - Full system installation"
    echo "  update    - Update application code and dependencies"
    echo "  start     - Start the service"
    echo "  stop      - Stop the service"
    echo "  restart   - Restart the service"
    echo "  status    - Show system status"
    echo ""
}

# Main script logic
case "$1" in
    install)
        check_root
        install_dependencies
        setup_directories
        setup_python_environment
        setup_application
        setup_systemd_service
        setup_nginx
        setup_firewall
        deploy_application
        print_success "Installation complete!"
        echo ""
        echo "Next steps:"
        echo "1. Edit $APP_DIR/.env with your Binance API keys"
        echo "2. Restart the service: $0 restart"
        echo "3. Access the web interface at http://your-server-ip"
        ;;
    update)
        check_root
        deploy_application
        print_success "Update complete!"
        ;;
    start)
        check_root
        start_service
        ;;
    stop)
        check_root
        stop_service
        ;;
    restart)
        check_root
        restart_service
        ;;
    status)
        show_status
        ;;
    *)
        show_usage
        exit 1
        ;;
esac

exit 0