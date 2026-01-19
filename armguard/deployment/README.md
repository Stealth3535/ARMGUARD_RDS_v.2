# ArmGuard Deployment Scripts

This directory contains deployment and management scripts for ArmGuard on Ubuntu/Raspberry Pi.

---

## 📋 Available Scripts

### 🚀 Initial Deployment
**`deploy-armguard.sh`** - Complete automated first-time deployment
```bash
sudo bash deployment/deploy-armguard.sh
```
- Fresh installation
- Creates database
- Configures services
- Sets up Python environment
- Installs dependencies

### ✅ Safe Update (Preserves Data)
**`update-armguard.sh`** - Update code without losing data ⭐ **RECOMMENDED**
```bash
sudo bash deployment/update-armguard.sh
```
- ✅ **Automatically backs up database**
- ✅ **Preserves all your data**
- ✅ Updates code from GitHub
- ✅ Installs new dependencies
- ✅ Runs migrations safely
- ✅ Restarts services
- ✅ Verifies deployment

**Use this for:**
- Pulling security fixes
- Getting new features
- Bug fixes
- Regular updates

### ♻️ Complete Reinstall
**`cleanup-and-deploy.sh`** - Remove everything and start fresh
```bash
sudo bash deployment/cleanup-and-deploy.sh
```
- ⚠️ **DELETES all data**
- Removes database
- Fresh installation
- **Only use for testing or major issues!**

### ✔️ Pre-Deployment Check
**`pre-check.sh`** - Validate environment before deployment
```bash
sudo bash deployment/pre-check.sh
```
- Checks internet connectivity
- Validates Python installation
- Verifies disk space
- Tests port availability

### 🔧 Service Installer
**`install-gunicorn-service.sh`** - Install/update Gunicorn service only
```bash
sudo bash deployment/install-gunicorn-service.sh
```
- Updates systemd service
- Doesn't touch code or data

### 🌐 Web Server Setup
**`install-nginx.sh`** - Install and configure Nginx
```bash
sudo bash deployment/install-nginx.sh [domain]
```
- Installs Nginx web server
- Configures reverse proxy to Gunicorn
- Sets up static/media file serving
- Adds security headers
- Configures firewall (UFW)

**Example with custom domain:**
```bash
sudo bash deployment/install-nginx.sh armguard.local
```

### 🔐 SSL/HTTPS Setup
**`install-mkcert-ssl.sh`** - Install SSL certificates (local development)
```bash
sudo bash deployment/install-mkcert-ssl.sh [domain]
```
- Installs mkcert (supports ARM64 for Raspberry Pi)
- Generates self-signed SSL certificates
- Configures Nginx for HTTPS
- Enables HTTP → HTTPS redirect
- Adds SSL security headers

**Example with custom domain:**
```bash
sudo bash deployment/install-mkcert-ssl.sh armguard.local
```

**⚠️ Note:** For production servers accessible from the internet, use Let's Encrypt instead (see [NGINX_SSL_GUIDE.md](NGINX_SSL_GUIDE.md))

---

## 🎯 Quick Usage Guide

### First Time Setup
```bash
# On your Raspberry Pi 5 / Ubuntu Server
# Create directory and clone repository
sudo mkdir -p /var/www
cd /var/www
sudo git clone https://github.com/Stealth3535/armguard.git
cd armguard

# Optional: Validate environment first
sudo bash deployment/pre-check.sh

# Deploy application
sudo bash deployment/deploy-armguard.sh

# Install web server (Nginx)
sudo bash deployment/install-nginx.sh

# Optional: Install SSL/HTTPS
sudo bash deployment/install-mkcert-ssl.sh
```

### Regular Updates (With Data)
```bash
cd /var/www/armguard
sudo bash deployment/update-armguard.sh    # One command - done!
```

**That's it!** The update script handles everything automatically:
- Backs up your database
- Updates code
- Installs dependencies
- Runs migrations
- Restarts services

---

## 🌐 Web Server & SSL Setup

### Nginx Installation
After deploying ArmGuard, install Nginx to serve your application:

```bash
cd /var/www/armguard
sudo bash deployment/install-nginx.sh
```

**Access your application:**
- HTTP: `http://your-server-ip`
- Or with custom domain: `http://armguard.local`

### SSL/HTTPS Setup (Optional)

**For local development/testing:**
```bash
sudo bash deployment/install-mkcert-ssl.sh
```

**For production (internet-accessible):**
```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Generate Let's Encrypt certificate
sudo certbot --nginx -d yourdomain.com
```

**Access with HTTPS:**
- `https://your-server-ip`
- Or: `https://yourdomain.com`

**📖 Complete Nginx & SSL Guide:** [NGINX_SSL_GUIDE.md](NGINX_SSL_GUIDE.md)

---

## Quick Setup (Manual Method)

### 1. Install Gunicorn (if not already in venv)
```bash
cd /var/www/armguard
source .venv/bin/activate
pip install gunicorn
```

### 2. Copy Service File
```bash
sudo cp deployment/gunicorn-armguard.service /etc/systemd/system/
```

### 3. Update Service File Paths
Edit `/etc/systemd/system/gunicorn-armguard.service` and adjust:
- `User` and `Group` (default: www-data)
- `WorkingDirectory` (your project path)
- `--workers` count (formula: 2 × CPU cores + 1)

### 4. Create Log Directory
```bash
sudo mkdir -p /var/log/armguard
sudo chown www-data:www-data /var/log/armguard
```

### 5. Set Permissions
```bash
sudo chown -R www-data:www-data /var/www/armguard
sudo chmod 600 /var/www/armguard/.env
```

### 6. Start Service
```bash
sudo systemctl daemon-reload
sudo systemctl start gunicorn-armguard
sudo systemctl enable gunicorn-armguard
```

---

## Service Management Commands

### Check Status
```bash
sudo systemctl status gunicorn-armguard
```

### Start Service
```bash
sudo systemctl start gunicorn-armguard
```

### Stop Service
```bash
sudo systemctl stop gunicorn-armguard
```

### Restart Service
```bash
sudo systemctl restart gunicorn-armguard
```

### Reload Configuration (graceful restart)
```bash
sudo systemctl reload gunicorn-armguard
```

### Enable Auto-Start on Boot
```bash
sudo systemctl enable gunicorn-armguard
```

### Disable Auto-Start
```bash
sudo systemctl disable gunicorn-armguard
```

---

## View Logs

### Real-time Logs (Follow)
```bash
# Systemd journal
sudo journalctl -u gunicorn-armguard -f

# Access logs
sudo tail -f /var/log/armguard/access.log

# Error logs
sudo tail -f /var/log/armguard/error.log
```

### Recent Logs (Last 50 lines)
```bash
sudo journalctl -u gunicorn-armguard -n 50
```

### Logs Since Boot
```bash
sudo journalctl -u gunicorn-armguard -b
```

### Logs for Specific Time Period
```bash
# Today
sudo journalctl -u gunicorn-armguard --since today

# Last hour
sudo journalctl -u gunicorn-armguard --since "1 hour ago"

# Between dates
sudo journalctl -u gunicorn-armguard --since "2025-11-01" --until "2025-11-08"
```

---

## Worker Configuration

### Calculate Optimal Workers
Formula: `(2 × CPU cores) + 1`

**Check CPU cores:**
```bash
nproc
```

**Examples:**
- 1 CPU core: 3 workers
- 2 CPU cores: 5 workers
- 4 CPU cores: 9 workers
- 8 CPU cores: 17 workers

**Edit worker count in service file:**
```bash
sudo nano /etc/systemd/system/gunicorn-armguard.service
```

Change line:
```
--workers 3 \
```

Then reload:
```bash
sudo systemctl daemon-reload
sudo systemctl restart gunicorn-armguard
```

---

## Troubleshooting

### Service Won't Start
1. **Check logs:**
   ```bash
   sudo journalctl -u gunicorn-armguard -n 50
   ```

2. **Test Gunicorn manually:**
   ```bash
   cd /var/www/armguard
   source .venv/bin/activate
   gunicorn --bind 127.0.0.1:8000 core.wsgi:application
   ```

3. **Check permissions:**
   ```bash
   sudo ls -la /var/www/armguard
   sudo ls -la /var/www/armguard/.env
   ```

4. **Verify socket directory:**
   ```bash
   sudo ls -la /run/ | grep gunicorn
   ```

### Socket File Not Created
1. **Check if directory exists:**
   ```bash
   ls -ld /run
   ```

2. **Try different socket location:**
   Edit service file to use `/tmp/gunicorn-armguard.sock`

### Permission Denied Errors
```bash
# Fix ownership
sudo chown -R www-data:www-data /var/www/armguard

# Fix .env permissions
sudo chmod 600 /var/www/armguard/.env
sudo chown www-data:www-data /var/www/armguard/.env

# Fix database permissions (if using SQLite)
sudo chmod 664 /var/www/armguard/db.sqlite3
sudo chown www-data:www-data /var/www/armguard/db.sqlite3
```

### High Memory Usage
1. **Reduce worker count**
2. **Add `--max-requests` to restart workers:**
   ```
   --max-requests 1000 \
   --max-requests-jitter 50 \
   ```

### Slow Response Times
1. **Increase workers**
2. **Increase timeout:**
   ```
   --timeout 120 \
   ```

---

## Performance Tuning

### Recommended Settings

**For Production Server (2GB RAM, 2 CPU):**
```
--workers 5
--worker-class sync
--timeout 60
--max-requests 1000
--max-requests-jitter 50
```

**For High Traffic (4GB+ RAM, 4+ CPU):**
```
--workers 9
--worker-class gthread
--threads 2
--timeout 60
--max-requests 1000
--max-requests-jitter 50
```

**For Low Memory Server (Raspberry Pi, <2GB):**
```
--workers 3
--worker-class sync
--timeout 60
--max-requests 500
```

### Edit Service File
```bash
sudo nano /etc/systemd/system/gunicorn-armguard.service
```

After changes:
```bash
sudo systemctl daemon-reload
sudo systemctl restart gunicorn-armguard
```

---

## Security Enhancements

### 1. Run as Non-Privileged User
Service file already configured with:
```
User=www-data
Group=www-data
```

### 2. Private /tmp Directory
```
PrivateTmp=true
```

### 3. Prevent Privilege Escalation
```
NoNewPrivileges=true
```

### 4. Restrict File Access (Optional)
Add to service file:
```
ReadWritePaths=/var/www/armguard/media
ReadWritePaths=/var/log/armguard
ReadOnlyPaths=/var/www/armguard
ProtectSystem=strict
ProtectHome=true
```

---

## Monitoring & Health Checks

### Check if Gunicorn is Running
```bash
ps aux | grep gunicorn
```

### Check Socket File
```bash
sudo ls -la /run/gunicorn-armguard.sock
```

### Test Socket Connection
```bash
curl --unix-socket /run/gunicorn-armguard.sock http://localhost/
```

### Monitor Resource Usage
```bash
# Install htop
sudo apt install htop

# Run
htop
# Filter: F4 > gunicorn
```

### Check Open Connections
```bash
sudo ss -tulpn | grep gunicorn
```

---

## Backup Service File

Before making changes:
```bash
sudo cp /etc/systemd/system/gunicorn-armguard.service \
       /etc/systemd/system/gunicorn-armguard.service.backup
```

---

## Multiple Apps on Same Server

### For Second App
1. **Copy and rename service file:**
   ```bash
   sudo cp /etc/systemd/system/gunicorn-armguard.service \
          /etc/systemd/system/gunicorn-webapp2.service
   ```

2. **Edit new service file:**
   - Change `Description`
   - Change `WorkingDirectory`
   - Change socket path: `/run/gunicorn-webapp2.sock`
   - Update log paths

3. **Start second service:**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl start gunicorn-webapp2
   sudo systemctl enable gunicorn-webapp2
   ```

---

## Integration with Nginx

Nginx should proxy to the Gunicorn socket. See `UBUNTU_MKCERT_SSL_SETUP.md` for complete Nginx configuration.

**Quick Nginx config snippet:**
```nginx
location / {
    proxy_pass http://unix:/run/gunicorn-armguard.sock;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

---

## Auto-Restart on Failure

Service file already configured with:
```
Restart=always
RestartSec=3
```

This means:
- Gunicorn auto-restarts if it crashes
- Waits 3 seconds before restarting
- No manual intervention needed

---

## Summary

**Service File Location:** `/etc/systemd/system/gunicorn-armguard.service`

**Socket Location:** `/run/gunicorn-armguard.sock`

**Log Locations:**
- Access: `/var/log/armguard/access.log`
- Error: `/var/log/armguard/error.log`
- Systemd: `journalctl -u gunicorn-armguard`

**Common Commands:**
```bash
# Status
sudo systemctl status gunicorn-armguard

# Restart
sudo systemctl restart gunicorn-armguard

# Logs
sudo journalctl -u gunicorn-armguard -f
```

---

## 📚 Documentation Index

| Document | Description |
|----------|-------------|
| [README.md](README.md) | This file - deployment scripts guide |
| [NGINX_SSL_GUIDE.md](NGINX_SSL_GUIDE.md) | Complete Nginx & SSL setup guide |
| [QUICK_DEPLOY.md](QUICK_DEPLOY.md) | Quick deployment reference |
| [../DEPLOYMENT_GUIDE.md](../DEPLOYMENT_GUIDE.md) | Complete deployment guide |
| [../ADMIN_GUIDE.md](../ADMIN_GUIDE.md) | Administrator operations guide |
| [../TESTING_GUIDE.md](../TESTING_GUIDE.md) | Testing procedures |
| [../FINAL_TEST_REPORT.md](../FINAL_TEST_REPORT.md) | Comprehensive test results |
| [../DEPLOYMENT_READY.md](../DEPLOYMENT_READY.md) | Final deployment summary |

---

## 🎯 Quick Command Reference

```bash
# Application Management
sudo systemctl status gunicorn-armguard    # Check status
sudo systemctl restart gunicorn-armguard   # Restart app
sudo systemctl stop gunicorn-armguard      # Stop app
sudo systemctl start gunicorn-armguard     # Start app

# Web Server Management
sudo systemctl status nginx                # Check Nginx
sudo systemctl restart nginx               # Restart Nginx
sudo nginx -t                              # Test config

# Updates (Preserves Data)
sudo bash deployment/update-armguard.sh    # Safe update

# Logs
sudo journalctl -u gunicorn-armguard -f   # App logs
sudo tail -f /var/log/nginx/armguard_access.log  # Access logs
sudo tail -f /var/log/nginx/armguard_error.log   # Error logs

# Database Backup (Manual)
sudo cp /var/www/armguard/db.sqlite3 \
        /var/www/armguard/db.sqlite3.backup_$(date +%Y%m%d_%H%M%S)
```

---

## ✅ Post-Installation Checklist

After deployment, verify:

- [ ] Application accessible via HTTP
- [ ] Can login with superuser credentials
- [ ] Dashboard loads correctly
- [ ] Static files (CSS/JS) loading
- [ ] Media files (images/QR codes) loading
- [ ] Can create personnel records
- [ ] Can create inventory items
- [ ] QR codes generate automatically
- [ ] Transactions can be created
- [ ] Gunicorn service running
- [ ] Nginx service running (if installed)
- [ ] SSL certificate working (if installed)
- [ ] Automatic backup working

---

## 🆘 Need Help?

1. **Check logs first:**
   ```bash
   sudo journalctl -u gunicorn-armguard -n 50
   sudo tail -f /var/log/nginx/armguard_error.log
   ```

2. **Review documentation:**
   - Troubleshooting sections in guides
   - Error messages in logs
   - Django debug output (if DEBUG=True)

3. **Common issues:**
   - 502 Bad Gateway → Gunicorn not running
   - Static files not loading → Run collectstatic
   - Permission denied → Check file ownership
   - Database locked → Check permissions on db.sqlite3

---

**Created:** November 8, 2025  
**Last Updated:** November 8, 2025  
**Version:** 2.0
