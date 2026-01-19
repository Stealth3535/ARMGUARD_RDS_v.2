# ArmGuard Deployment Guide

## Quick Start (Development)

### 1. Prerequisites
- Python 3.12+ installed
- pip package manager
- Git (optional)

### 2. Installation

```bash
# Navigate to project directory
cd "d:\ GUI projects\3\armguard"

# Create virtual environment
python -m venv .venv

# Activate virtual environment (Windows PowerShell)
.venv\Scripts\Activate.ps1

# Activate virtual environment (Windows Command Prompt)
.venv\Scripts\activate.bat

# Activate virtual environment (Linux/Mac)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Database Setup

```bash
# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

### 4. Create Admin Groups

```bash
# Run utility script to create groups
python assign_user_groups.py
```

### 5. Run Development Server

```bash
python manage.py runserver
```

Access the application at: `http://127.0.0.1:8000/`

---

## Production Deployment

### Architecture Overview

**System-wide installations** (shared across all apps):
- ✅ **Nginx** - Reverse proxy and web server
- ✅ **mkcert** - SSL certificate tool for LAN deployments

**Virtual environment** (per-app):
- ✅ **Gunicorn** - WSGI HTTP server (each app has its own version)
- ✅ Django and app-specific dependencies (from `requirements.txt`)

**Why this approach?**
- One Nginx installation routes to multiple apps
- Each app runs in isolation with its own Gunicorn version
- Prevents dependency conflicts between apps
- Easy to update/maintain individual apps without affecting others
- Supports both LAN and public-facing apps on the same server

---

### Option A: Windows Server (IIS + wfastcgi)

#### 1. Install Dependencies

```powershell
# Install Python 3.12+
# Download from https://www.python.org/downloads/

# Install IIS with CGI
Install-WindowsFeature -name Web-Server -IncludeManagementTools
Install-WindowsFeature -name Web-CGI

# Install wfastcgi
pip install wfastcgi
wfastcgi-enable
```

#### 2. Configure Environment

```powershell
# Create .env file from template
copy .env.example .env

# Edit .env with production values
notepad .env
```

Required `.env` changes:
```
DJANGO_SECRET_KEY=<generate-new-random-key>
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=your-server-ip,your-domain.com
```

#### 3. Collect Static Files

```powershell
python manage.py collectstatic --noinput
```

#### 4. Configure IIS

Create `web.config` in project root:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
  <system.webServer>
    <handlers>
      <add name="Python FastCGI" path="*" verb="*" modules="FastCgiModule" scriptProcessor="C:\Path\To\Python\python.exe|C:\Path\To\Python\Scripts\wfastcgi.py" resourceType="Unspecified" requireAccess="Script" />
    </handlers>
  </system.webServer>
  <appSettings>
    <add key="PYTHONPATH" value="D:\GUI projects\3\armguard" />
    <add key="WSGI_HANDLER" value="core.wsgi.application" />
    <add key="DJANGO_SETTINGS_MODULE" value="core.settings" />
  </appSettings>
</configuration>
```

#### 5. Set File Permissions

- Give IIS_IUSRS read/write access to:
  - `db.sqlite3`
  - `media/` folder
  - `logs/` folder (create if needed)

---

### Option B: Linux Server (Nginx + Gunicorn)

#### 1. Install System Dependencies

```bash
sudo apt update
sudo apt install python3.12 python3-pip python3-venv nginx

# Start and enable Nginx
sudo systemctl start nginx
sudo systemctl enable nginx
```

**Note:** Nginx is installed **system-wide** to serve as a reverse proxy for all apps. Gunicorn will be installed in each app's virtual environment.

#### 2. Setup Application

```bash
# Create application directory
sudo mkdir -p /var/www/armguard
sudo chown $USER:$USER /var/www/armguard
cd /var/www/armguard

# Copy application files
# (Use git clone or scp to transfer files)

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies (includes Gunicorn)
pip install -r requirements.txt
```

#### 3. Configure Environment

```bash
# Create .env file
cp .env.example .env
nano .env
```

Set production values:
```
DJANGO_SECRET_KEY=<generate-new-random-key>
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=your-server-ip,your-domain.com
```

#### 4. Configure settings.py for Production

Create `core/settings_production.py`:
```python
from .settings import *
from decouple import config

DEBUG = False
ALLOWED_HOSTS = config('DJANGO_ALLOWED_HOSTS').split(',')

# Security
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Static files
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Database (consider PostgreSQL)
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': config('DB_NAME'),
#         'USER': config('DB_USER'),
#         'PASSWORD': config('DB_PASSWORD'),
#         'HOST': config('DB_HOST'),
#         'PORT': config('DB_PORT'),
#     }
# }
```

#### 5. Collect Static Files & Migrate

```bash
export DJANGO_SETTINGS_MODULE=core.settings_production
python manage.py collectstatic --noinput
python manage.py migrate
```

#### 6. Create Systemd Service

Create `/etc/systemd/system/gunicorn-armguard.service`:
```ini
[Unit]
Description=ArmGuard Gunicorn daemon
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/armguard
Environment="PATH=/var/www/armguard/.venv/bin"
Environment="DJANGO_SETTINGS_MODULE=core.settings_production"
EnvironmentFile=/var/www/armguard/.env
ExecStart=/var/www/armguard/.venv/bin/gunicorn \
    --workers 3 \
    --bind unix:/run/gunicorn-armguard.sock \
    core.wsgi:application
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

**Key points:**
- Uses Gunicorn from the app's virtual environment (`.venv/bin/gunicorn`)
- Each app has its own Gunicorn version, preventing dependency conflicts
- Socket path includes app name (`gunicorn-armguard.sock`) for multi-app support
- Auto-restart on failure ensures high availability

Set permissions and start service:
```bash
# Set proper ownership
sudo chown -R www-data:www-data /var/www/armguard

# Start and enable service
sudo systemctl daemon-reload
sudo systemctl start gunicorn-armguard
sudo systemctl enable gunicorn-armguard
sudo systemctl status gunicorn-armguard
```

#### 7. Configure Nginx

Create `/etc/nginx/sites-available/armguard`:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location = /favicon.ico { access_log off; log_not_found off; }
    
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

Enable site:
```bash
sudo ln -s /etc/nginx/sites-available/armguard /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

#### 8. SSL Certificate

**For Public Domains (Let's Encrypt):**
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

**For LAN/Local Deployments (mkcert):**

See the comprehensive guide: [UBUNTU_MKCERT_SSL_SETUP.md](./UBUNTU_MKCERT_SSL_SETUP.md)

Quick setup:
```bash
# Install mkcert (system-wide)
wget https://github.com/FiloSottile/mkcert/releases/download/v1.4.4/mkcert-v1.4.4-linux-amd64
sudo mv mkcert-v1.4.4-linux-amd64 /usr/local/bin/mkcert
sudo chmod +x /usr/local/bin/mkcert

# Create CA and generate certificates
mkcert -install
mkcert your-server-ip localhost 127.0.0.1

# Follow UBUNTU_MKCERT_SSL_SETUP.md for complete configuration
```

---

## Database Migration (SQLite to PostgreSQL)

### 1. Install PostgreSQL

**Windows:**
- Download from https://www.postgresql.org/download/windows/

**Linux:**
```bash
sudo apt install postgresql postgresql-contrib
```

### 2. Create Database

```bash
sudo -u postgres psql
```

```sql
CREATE DATABASE armguard_db;
CREATE USER armguard_user WITH PASSWORD 'secure_password_here';
ALTER ROLE armguard_user SET client_encoding TO 'utf8';
ALTER ROLE armguard_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE armguard_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE armguard_db TO armguard_user;
\q
```

### 3. Update settings.py

```python
pip install psycopg2-binary

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'armguard_db',
        'USER': 'armguard_user',
        'PASSWORD': 'secure_password_here',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

### 4. Migrate Data

```bash
# Backup SQLite database
python manage.py dumpdata > backup.json

# Switch to PostgreSQL in settings.py

# Run migrations
python manage.py migrate

# Load data
python manage.py loaddata backup.json
```

---

## Security Checklist

Before going live, ensure:

- [ ] SECRET_KEY is randomized and in .env file
- [ ] DEBUG=False
- [ ] ALLOWED_HOSTS configured
- [ ] HTTPS/SSL certificate installed
- [ ] SECURE_* settings enabled in production
- [ ] Database backups configured
- [ ] Static files collected
- [ ] Media files folder has proper permissions
- [ ] .env file is NOT in version control
- [ ] Strong database passwords
- [ ] Firewall configured (allow only HTTP/HTTPS)
- [ ] Regular security updates scheduled

---

## Maintenance

### Backup Database

```bash
# SQLite
cp db.sqlite3 db.sqlite3.backup.$(date +%Y%m%d)

# PostgreSQL
pg_dump -U armguard_user armguard_db > backup_$(date +%Y%m%d).sql
```

### Update Application

```bash
# Pull latest code
git pull origin main

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Restart service (Linux)
sudo systemctl restart gunicorn-armguard
sudo systemctl reload nginx

# Restart IIS (Windows)
iisreset
```

### Monitor Logs

```bash
# Gunicorn logs
sudo journalctl -u gunicorn-armguard -f
sudo journalctl -u gunicorn-armguard -n 50  # Last 50 lines

# Nginx logs
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log

# Django logs
tail -f logs/django_errors.log

# Check service status
sudo systemctl status gunicorn-armguard
sudo systemctl status nginx
```

---

## Troubleshooting

### Issue: Static files not loading
**Solution:**
```bash
python manage.py collectstatic --noinput
# Check STATIC_ROOT and STATIC_URL in settings
```

### Issue: Database connection error
**Solution:**
- Check database credentials in .env
- Ensure PostgreSQL service is running
- Check pg_hba.conf for connection permissions

### Issue: Permission denied errors
**Solution:**
```bash
# Linux
sudo chown -R www-data:www-data /var/www/armguard
sudo chmod -R 755 /var/www/armguard

# Windows
# Give IIS_IUSRS appropriate permissions
```

### Issue: 500 Internal Server Error
**Solution:**
- Check DEBUG=True temporarily to see error
- Check logs in logs/django_errors.log
- Verify all migrations are applied
- Check ALLOWED_HOSTS configuration

---

## Support

For issues or questions:
1. Check the CODE_REVIEW_REPORT.md
2. Review Django logs
3. Consult Django documentation: https://docs.djangoproject.com/

---

## Additional Resources

- **LAN/Local SSL Setup**: [UBUNTU_MKCERT_SSL_SETUP.md](./UBUNTU_MKCERT_SSL_SETUP.md)
- **Ubuntu Quick Install**: [UBUNTU_INSTALL.md](./UBUNTU_INSTALL.md)
- **Security Hardening**: [SECURITY_FIXES_APPLIED.md](./SECURITY_FIXES_APPLIED.md)
- **Online Testing Security**: [SECURITY_ONLINE_TESTING.md](./SECURITY_ONLINE_TESTING.md) - **Read this before exposing app to internet**

---

**Last Updated:** November 8, 2025
