# Deployment Guide for Ubuntu 24.04 LTS

This guide covers deploying the RAG Document Manager application to an Ubuntu 24.04 LTS server.

## Prerequisites

- Ubuntu 24.04 LTS server
- Root or sudo access
- Domain name (optional, for production)
- At least 2GB RAM recommended

## Deployment Options

### Option 1: Quick Deployment (Recommended for Testing)
Uses the provided deployment script for automated setup.

### Option 2: Manual Deployment with Gunicorn + Nginx
Full production setup with reverse proxy.

### Option 3: Docker Deployment
Containerized deployment (if Docker is available).

---

## Option 1: Quick Deployment Script

### Step 1: Connect to Your Server

```bash
ssh root@server
```

### Step 2: Update System

```bash
apt update && apt upgrade -y
```

### Step 3: Install Required System Packages

```bash
apt install -y python3 python3-pip python3-venv git nginx
```

### Step 4: Clone/Upload Application

```bash
# Create application directory
mkdir -p /opt/rag-app
cd /opt/rag-app

# Upload your app-1 directory here
# You can use scp, rsync, or git
```

If using scp from your local machine:
```bash
# Run this from your local machine
cd /Users/pc/dev/techbubble/ai-bot
scp -r app-1 root@server:/opt/rag-app/
```

### Step 5: Run Deployment Script

```bash
cd /opt/rag-app/app-1
chmod +x deploy.sh
./deploy.sh
```

The script will:
- Install Python dependencies
- Create systemd service
- Configure environment
- Initialize database
- Start the application

### Step 6: Access the Application

```bash
# Check service status
systemctl status rag-app

# View logs
journalctl -u rag-app -f
```

Application will be available at:
- **Web Interface**: http://your-server-ip:5000
- **API**: http://your-server-ip:5000/api/*

---

## Option 2: Manual Production Deployment

### Step 1: System Preparation

```bash
# Update system
apt update && apt upgrade -y

# Install dependencies
apt install -y python3 python3-pip python3-venv git nginx supervisor
```

### Step 2: Create Application User

```bash
# Create dedicated user for security
useradd -m -s /bin/bash ragapp
```

### Step 3: Setup Application Directory

```bash
# Create directory
mkdir -p /opt/rag-app
cd /opt/rag-app

# Upload application files
# (Use scp, git, or your preferred method)

# Set ownership
chown -R ragapp:ragapp /opt/rag-app
```

### Step 4: Setup Python Environment

```bash
# Switch to application user
su - ragapp

# Navigate to app directory
cd /opt/rag-app/app-1

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# Install production server
pip install gunicorn
```

### Step 5: Create Production Configuration

Create `/opt/rag-app/app-1/.env`:
```bash
FLASK_ENV=production
SECRET_KEY=your-secret-key-change-this
DATABASE_URL=sqlite:///instance/ragapp.db
```

### Step 6: Initialize Database

```bash
# Still as ragapp user
cd /opt/rag-app/app-1
source venv/bin/activate
python << 'EOF'
from app import app, db
with app.app_context():
    db.create_all()
    print("Database initialized")
EOF
```

### Step 7: Create Systemd Service

Create `/etc/systemd/system/rag-app.service`:
```ini
[Unit]
Description=RAG Document Manager
After=network.target

[Service]
Type=notify
User=ragapp
Group=ragapp
WorkingDirectory=/opt/rag-app/app-1
Environment="PATH=/opt/rag-app/app-1/venv/bin"
ExecStart=/opt/rag-app/app-1/venv/bin/gunicorn --workers 4 --bind 127.0.0.1:5000 --timeout 300 --access-logfile - --error-logfile - app:app

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
systemctl daemon-reload
systemctl enable rag-app
systemctl start rag-app
systemctl status rag-app
```

### Step 8: Configure Nginx Reverse Proxy

Create `/etc/nginx/sites-available/rag-app`:
```nginx
server {
    listen 80;
    server_name your-domain.com;  # Change this

    client_max_body_size 100M;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 300s;
    }

    location /static {
        alias /opt/rag-app/app-1/static;
        expires 30d;
    }
}
```

Enable site:
```bash
ln -s /etc/nginx/sites-available/rag-app /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx
```

### Step 9: Configure Firewall

```bash
# Allow HTTP/HTTPS
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 22/tcp  # SSH
ufw --force enable
```

### Step 10: SSL Certificate (Optional but Recommended)

```bash
# Install certbot
apt install -y certbot python3-certbot-nginx

# Get certificate
certbot --nginx -d your-domain.com

# Auto-renewal is configured automatically
```

---

## Option 3: Docker Deployment

See `docker-compose.yml` and `Dockerfile` for containerized deployment.

```bash
# Install Docker
apt install -y docker.io docker-compose

# Navigate to app directory
cd /opt/rag-app/app-1

# Build and run
docker-compose up -d

# View logs
docker-compose logs -f
```

---

## Post-Deployment

### Monitoring

```bash
# Check application status
systemctl status rag-app

# View logs
journalctl -u rag-app -f

# Nginx logs
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

### Maintenance

```bash
# Restart application
systemctl restart rag-app

# Update application
cd /opt/rag-app/app-1
git pull  # or upload new files
systemctl restart rag-app

# Backup database
cp /opt/rag-app/app-1/instance/ragapp.db /backup/ragapp.db.$(date +%Y%m%d)
```

### Security Checklist

- [ ] Change default SECRET_KEY in .env
- [ ] Configure firewall (ufw)
- [ ] Setup SSL certificate
- [ ] Regular system updates
- [ ] Setup automated backups
- [ ] Monitor disk space (vector database can grow)
- [ ] Setup log rotation

---

## Troubleshooting

### Application won't start

```bash
# Check logs
journalctl -u rag-app -n 50

# Check if port is in use
netstat -tlnp | grep 5000

# Test application manually
cd /opt/rag-app/app-1
source venv/bin/activate
python app.py
```

### Nginx errors

```bash
# Test configuration
nginx -t

# Check logs
tail -f /var/log/nginx/error.log
```

### Database issues

```bash
# Reset database (WARNING: deletes all data)
rm /opt/rag-app/app-1/instance/ragapp.db
# Then reinitialize using Step 6
```

### Permission issues

```bash
# Fix ownership
chown -R ragapp:ragapp /opt/rag-app
```

---

## Performance Tuning

### For Production

1. **Gunicorn Workers**: Adjust based on CPU cores
   ```
   workers = (2 x CPU_CORES) + 1
   ```

2. **Increase File Upload Limit**: Edit nginx config
   ```nginx
   client_max_body_size 500M;
   ```

3. **Database**: Consider PostgreSQL for production
   - Better concurrent access
   - More reliable for production

4. **Vector Database**: Monitor ChromaDB size
   - Implement cleanup policies
   - Consider separate disk/volume

---

## Support

For issues specific to:
- **Application**: Check app logs and README.md
- **Server**: Ubuntu documentation
- **Nginx**: Nginx documentation
- **SSL**: Certbot documentation

## Quick Commands Reference

```bash
# Service management
systemctl start rag-app
systemctl stop rag-app
systemctl restart rag-app
systemctl status rag-app

# View logs
journalctl -u rag-app -f
tail -f /var/log/nginx/access.log

# Nginx
systemctl restart nginx
nginx -t

# Firewall
ufw status
ufw allow 80/tcp
```
