# ArmGuard - Ubuntu Server Installation Guide

Quick installation guide for Ubuntu Server (including Raspberry Pi Ubuntu Server).

---

## Prerequisites

- Ubuntu Server 20.04+ or Raspberry Pi OS (64-bit)
- Python 3.10+
- Internet connection
- Sudo privileges

---

## Quick Install (5 Minutes)

```bash
# 1. Update system
sudo apt update && sudo apt upgrade -y

# 2. Install system dependencies
sudo apt install -y python3 python3-pip python3-venv git nginx postgresql postgresql-contrib

# 3. Install image libraries (for QR code generation)
sudo apt install -y libjpeg-dev zlib1g-dev

# 4. Clone repository
cd /var/www
sudo git clone https://github.com/Stealth3535/armguard.git
sudo chown -R $USER:$USER /var/www/armguard
cd armguard

# 5. Setup Python virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 6. Install Python packages (includes Gunicorn)
pip install --upgrade pip
pip install -r requirements.txt
pip install psycopg2-binary

# 7. Configure environment
cp .env.example .env
nano .env
# Edit: Set DJANGO_SECRET_KEY, DJANGO_DEBUG=False, DJANGO_ALLOWED_HOSTS

# 8. Setup database
python manage.py migrate
python manage.py createsuperuser
python assign_user_groups.py
python manage.py collectstatic --noinput

# 9. Test
python manage.py check --deploy
```

**Note:** Gunicorn is installed in each app's virtual environment for better isolation when running multiple apps.

---

## Production Deployment

### 1. Setup PostgreSQL

```bash
sudo -u postgres psql

# In PostgreSQL:
CREATE DATABASE armguard_db;
CREATE USER armguard_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE armguard_db TO armguard_user;
\q
```

### 2. Create Gunicorn Service

```bash
sudo nano /etc/systemd/system/gunicorn-armguard.service
```

Add:

```ini
[Unit]
Description=Gunicorn daemon for ArmGuard
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/armguard
Environment="PATH=/var/www/armguard/.venv/bin"
ExecStart=/var/www/armguard/.venv/bin/gunicorn \
    --workers 3 \
    --bind unix:/run/gunicorn-armguard.sock \
    core.wsgi:application
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

```bash
# Set permissions
sudo chown -R www-data:www-data /var/www/armguard

# Start and enable service
sudo systemctl daemon-reload
sudo systemctl start gunicorn-armguard
sudo systemctl enable gunicorn-armguard
sudo systemctl status gunicorn-armguard
```

### 3. Configure Nginx

```bash
sudo nano /etc/nginx/sites-available/armguard
```

Add:

```nginx
server {
    listen 80;
    server_name YOUR_SERVER_IP;

    location /static/ {
        alias /var/www/armguard/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /media/ {
        alias /var/www/armguard/media/;
        expires 7d;
    }

    location / {
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_pass http://unix:/run/gunicorn-armguard.sock;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/armguard /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 4. Setup Firewall

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
```

---

## Access Application

Open browser: `http://YOUR_SERVER_IP`

Admin panel: `http://YOUR_SERVER_IP/admin/`

---

## Quick Commands

```bash
# Check status
sudo systemctl status gunicorn-armguard
sudo systemctl status nginx

# Restart services
sudo systemctl restart gunicorn-armguard
sudo systemctl reload nginx

# View logs
sudo journalctl -u gunicorn-armguard -f
sudo journalctl -u gunicorn-armguard -n 50  # Last 50 lines
sudo tail -f /var/log/nginx/error.log

# Update from GitHub
cd /var/www/armguard
git pull origin main
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl restart gunicorn-armguard
```

---

## Troubleshooting

**Static files not loading:**
```bash
python manage.py collectstatic --clear --noinput
sudo systemctl restart nginx
```

**Gunicorn not starting:**
```bash
sudo journalctl -u gunicorn-armguard -n 50
sudo systemctl restart gunicorn-armguard
```

**Database errors:**
```bash
python manage.py migrate
sudo systemctl restart gunicorn-armguard
```

---

## SSL/HTTPS Setup

**For LAN/Local deployments**, see: [UBUNTU_MKCERT_SSL_SETUP.md](./UBUNTU_MKCERT_SSL_SETUP.md)

**For public deployments**, see: [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md) (Let's Encrypt section)

---

For detailed deployment guide, see: [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)
