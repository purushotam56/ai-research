#!/bin/bash

# RAG Document Manager - Production Deployment Script for Ubuntu 24.04
# This script automates the deployment process

set -e  # Exit on error

echo "🚀 RAG Document Manager - Production Deployment"
echo "================================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    print_error "Please run as root or with sudo"
    exit 1
fi

print_success "Running as root"

# Get the directory where script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
APP_DIR="/opt/rag-app/app-1"

echo ""
echo "Configuration:"
echo "  Script Location: $SCRIPT_DIR"
echo "  Deploy Location: $APP_DIR"
echo ""

# Ask for deployment location confirmation
read -p "Deploy to $APP_DIR? (y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    read -p "Enter deployment path: " APP_DIR
fi

echo ""
echo "Step 1: Updating system packages..."
apt update -qq
print_success "System packages updated"

echo ""
echo "Step 2: Installing required packages..."
apt install -y python3 python3-pip python3-venv git supervisor > /dev/null 2>&1
print_success "Required packages installed"

echo ""
echo "Step 3: Creating application user..."
if id "ragapp" &>/dev/null; then
    print_warning "User 'ragapp' already exists"
else
    useradd -m -s /bin/bash ragapp
    print_success "User 'ragapp' created"
fi

echo ""
echo "Step 4: Setting up application directory..."
mkdir -p $APP_DIR
if [ "$SCRIPT_DIR" != "$APP_DIR" ]; then
    echo "  Copying files from $SCRIPT_DIR to $APP_DIR..."
    cp -r $SCRIPT_DIR/* $APP_DIR/
    print_success "Files copied"
else
    print_warning "Already in deployment directory"
fi

# Create necessary directories
mkdir -p $APP_DIR/instance
mkdir -p $APP_DIR/uploads
mkdir -p $APP_DIR/vector_db
chown -R ragapp:ragapp $APP_DIR
print_success "Directory structure created"

echo ""
echo "Step 5: Setting up Python virtual environment..."
sudo -u ragapp python3 -m venv $APP_DIR/venv
print_success "Virtual environment created"

echo ""
echo "Step 6: Installing Python dependencies..."
echo "  This may take several minutes..."
sudo -u ragapp $APP_DIR/venv/bin/pip install --upgrade pip setuptools wheel > /dev/null 2>&1
sudo -u ragapp $APP_DIR/venv/bin/pip install -r $APP_DIR/requirements.txt
sudo -u ragapp $APP_DIR/venv/bin/pip install gunicorn
print_success "Python dependencies installed"

echo ""
echo "Step 7: Creating environment configuration..."
if [ ! -f "$APP_DIR/.env" ]; then
    SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')
    cat > $APP_DIR/.env << EOF
FLASK_ENV=production
SECRET_KEY=$SECRET_KEY
DATABASE_URL=sqlite:///instance/ragapp.db
EOF
    chown ragapp:ragapp $APP_DIR/.env
    print_success "Environment file created"
else
    print_warning ".env file already exists, skipping"
fi

echo ""
echo "Step 8: Initializing database..."
sudo -u ragapp $APP_DIR/venv/bin/python << 'EOF'
import sys
sys.path.insert(0, '/opt/rag-app/app-1')
from app import app, db
with app.app_context():
    db.create_all()
    print("Database initialized successfully")
EOF
print_success "Database initialized"

echo ""
echo "Step 9: Creating production WSGI entry point..."
cat > $APP_DIR/wsgi.py << 'EOF'
from app import app

if __name__ == "__main__":
    app.run()
EOF
chown ragapp:ragapp $APP_DIR/wsgi.py
print_success "WSGI entry point created"

echo ""
echo "Step 10: Creating systemd service..."
cat > /etc/systemd/system/rag-app.service << EOF
[Unit]
Description=RAG Document Manager Application
After=network.target

[Service]
Type=notify
User=ragapp
Group=ragapp
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/venv/bin"
ExecStart=$APP_DIR/venv/bin/gunicorn --workers 4 --bind 0.0.0.0:5000 --timeout 300 --access-logfile - --error-logfile - wsgi:app

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable rag-app
print_success "Systemd service created and enabled"

echo ""
echo "Step 11: Starting application..."
systemctl start rag-app
sleep 3

if systemctl is-active --quiet rag-app; then
    print_success "Application started successfully"
else
    print_error "Application failed to start"
    echo "Check logs with: journalctl -u rag-app -n 50"
    exit 1
fi

echo ""
echo "Step 12: Configuring firewall (if ufw is available)..."
if command -v ufw &> /dev/null; then
    ufw allow 5000/tcp > /dev/null 2>&1
    print_success "Firewall configured"
else
    print_warning "UFW not installed, skipping firewall configuration"
fi

echo ""
echo "================================================"
echo -e "${GREEN}✅ Deployment completed successfully!${NC}"
echo "================================================"
echo ""
echo "📊 Application Information:"
echo "  • Service: rag-app"
echo "  • Status: $(systemctl is-active rag-app)"
echo "  • Location: $APP_DIR"
echo "  • User: ragapp"
echo ""
echo "🌐 Access URLs:"
SERVER_IP=$(hostname -I | awk '{print $1}')
echo "  • Web Interface: http://$SERVER_IP:5000"
echo "  • API Endpoint: http://$SERVER_IP:5000/api"
echo ""
echo "📝 Useful Commands:"
echo "  • Check status: systemctl status rag-app"
echo "  • View logs: journalctl -u rag-app -f"
echo "  • Restart app: systemctl restart rag-app"
echo "  • Stop app: systemctl stop rag-app"
echo ""
echo "🔧 Next Steps (Optional):"
echo "  1. Setup Nginx reverse proxy (see DEPLOYMENT_GUIDE.md)"
echo "  2. Configure SSL certificate with certbot"
echo "  3. Setup automated backups"
echo ""
echo "📖 For detailed documentation, see: DEPLOYMENT_GUIDE.md"
echo ""
