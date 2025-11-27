#!/bin/bash

# Nginx Configuration Setup Script
# Run this after deploy.sh if you want to use Nginx as reverse proxy

set -e

echo "🔧 Setting up Nginx Reverse Proxy"
echo "=================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "❌ Please run as root or with sudo"
    exit 1
fi

# Install Nginx if not present
if ! command -v nginx &> /dev/null; then
    echo "📦 Installing Nginx..."
    apt update -qq
    apt install -y nginx
    echo "✓ Nginx installed"
else
    echo "✓ Nginx already installed"
fi

# Get server configuration
read -p "Enter your domain name (or press Enter to use server IP): " DOMAIN_NAME

if [ -z "$DOMAIN_NAME" ]; then
    DOMAIN_NAME=$(hostname -I | awk '{print $1}')
    echo "Using IP address: $DOMAIN_NAME"
fi

# Create Nginx configuration
echo ""
echo "📝 Creating Nginx configuration..."

cat > /etc/nginx/sites-available/rag-app << EOF
server {
    listen 80;
    server_name $DOMAIN_NAME;

    client_max_body_size 100M;
    client_body_timeout 300s;

    access_log /var/log/nginx/rag-app-access.log;
    error_log /var/log/nginx/rag-app-error.log;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # Timeouts
        proxy_read_timeout 300s;
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        
        # WebSocket support (if needed in future)
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Optional: Static files (if you add them)
    location /static {
        alias /opt/rag-app/app-1/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
EOF

# Enable site
echo "🔗 Enabling site..."
ln -sf /etc/nginx/sites-available/rag-app /etc/nginx/sites-enabled/

# Remove default site if it exists
if [ -f /etc/nginx/sites-enabled/default ]; then
    rm /etc/nginx/sites-enabled/default
    echo "✓ Removed default site"
fi

# Test configuration
echo ""
echo "🧪 Testing Nginx configuration..."
nginx -t

if [ $? -eq 0 ]; then
    echo "✓ Configuration valid"
    
    # Restart Nginx
    echo "🔄 Restarting Nginx..."
    systemctl restart nginx
    systemctl enable nginx
    echo "✓ Nginx restarted"
    
    # Update application to bind to localhost only
    echo ""
    echo "🔒 Updating application to bind to localhost..."
    
    # Update systemd service to bind to 127.0.0.1
    sed -i 's/0\.0\.0\.0:5000/127.0.0.1:5000/g' /etc/systemd/system/rag-app.service
    systemctl daemon-reload
    systemctl restart rag-app
    echo "✓ Application now accessible only through Nginx"
    
    # Configure firewall
    echo ""
    echo "🛡️ Configuring firewall..."
    if command -v ufw &> /dev/null; then
        ufw allow 'Nginx Full' > /dev/null 2>&1
        ufw delete allow 5000/tcp > /dev/null 2>&1 || true
        echo "✓ Firewall updated"
    fi
    
    echo ""
    echo "=================================="
    echo "✅ Nginx setup completed!"
    echo "=================================="
    echo ""
    echo "🌐 Your application is now accessible at:"
    echo "   http://$DOMAIN_NAME"
    echo ""
    echo "🔐 Optional: Setup SSL Certificate"
    echo ""
    echo "To enable HTTPS, run:"
    echo "  apt install -y certbot python3-certbot-nginx"
    echo "  certbot --nginx -d $DOMAIN_NAME"
    echo ""
    echo "📝 Nginx Commands:"
    echo "  • Test config: nginx -t"
    echo "  • Reload: systemctl reload nginx"
    echo "  • Restart: systemctl restart nginx"
    echo "  • Logs: tail -f /var/log/nginx/rag-app-error.log"
    echo ""
else
    echo "❌ Configuration test failed"
    exit 1
fi
