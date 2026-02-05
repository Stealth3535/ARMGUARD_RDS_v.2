# ArmGuard Quick Deployment Guide

## One-Command Deployment

Deploy ArmGuard automatically with a single command!

### Prerequisites
- Ubuntu 20.04+ or Debian 11+
- Root/sudo access
- Internet connection

### Quick Start

```bash
# 1. Clone or copy project to server
git clone https://github.com/yourusername/armguard.git /tmp/armguard

# 2. Run automated deployment
cd /tmp/armguard
sudo bash deployment/deploy-armguard.sh
```

That's it! The script will ask you a few questions and handle everything automatically.

---

## What the Script Does

The deployment script automatically:

✅ **System Setup**
- Updates system packages
- Installs Python, Nginx, PostgreSQL (optional)
- Configures security tools (UFW, Fail2Ban)

✅ **Application Setup**
- Creates virtual environment
- Installs Python dependencies
- Configures database (SQLite or PostgreSQL)
- Sets up secure environment variables
- Runs migrations
- Creates superuser account
- Collects static files

✅ **Web Server Setup**
- Installs and configures Gunicorn
- Creates systemd service with auto-restart
- Configures Nginx reverse proxy
- Sets up SSL/HTTPS (mkcert or Let's Encrypt)

✅ **Security Hardening**
- Configures firewall (UFW)
- Sets up Fail2Ban
- Applies secure file permissions
- Generates strong secrets
- Obfuscates admin URL

---

## Configuration Prompts

The script will ask you:

1. **Project directory** - Where to install (default: `/var/www/armguard`)
2. **Domain name** - Your domain or IP (default: `armguard.local`)
3. **Server IP** - Auto-detected, just press ENTER
4. **Run user** - User to run service (default: `www-data`)
5. **SSL/HTTPS** - Enable HTTPS? (default: `yes`)
   - **mkcert** - For LAN/local networks (easier)
   - **Let's Encrypt** - For public domains (free, auto-renewing)
6. **Database** - PostgreSQL or SQLite? (default: `SQLite`)
7. **Firewall** - Configure UFW? (default: `yes`)

**Pro tip:** Just press ENTER to accept all defaults for a standard installation!

---

## After Deployment

### Access Your Application

```
Main URL:    https://your-domain/
Admin URL:   https://your-domain/admin-XXXXXXXX/
```

The admin URL is randomized for security. You'll see it in the deployment summary.

### Check Service Status

```bash
# Check if services are running
sudo systemctl status gunicorn-armguard
sudo systemctl status nginx

# View real-time logs
sudo journalctl -u gunicorn-armguard -f
sudo tail -f /var/log/armguard/access.log
```

### Deployment Info File

All credentials and configuration details are saved to:
```
/var/www/armguard/DEPLOYMENT_INFO.txt
```

**Keep this file secure!** It contains:
- Django secret key
- Admin URL path
- Database credentials (if PostgreSQL)
- SSL certificate locations

---

## Common Scenarios

### Scenario 1: Local LAN Deployment (Simplest)

```bash
sudo bash deployment/deploy-armguard.sh
```

**Prompts to answer:**
- Domain: `armguard.local` (default)
- SSL: `yes` + mkcert (option 1)
- Database: `no` (SQLite, default)
- Everything else: Press ENTER for defaults

**Result:** Working HTTPS site on your local network

**Extra step:** Install CA certificate on client devices
```bash
# Copy from server
~/.local/share/mkcert/rootCA.pem
```

---

### Scenario 2: Public Internet Deployment

```bash
sudo bash deployment/deploy-armguard.sh
```

**Prompts to answer:**
- Domain: `armguard.yourdomain.com`
- SSL: `yes` + Let's Encrypt (option 2)
- Email: `admin@yourdomain.com`
- Database: `yes` (PostgreSQL recommended)
- Everything else: Press ENTER for defaults

**Prerequisites:**
- Domain must point to your server IP (DNS A record)
- Ports 80 and 443 must be open

**Result:** Production-ready HTTPS site with auto-renewing SSL

---

### Scenario 3: Multiple Apps on One Server

```bash
# Deploy first app
sudo bash deployment/deploy-armguard.sh
# Project dir: /var/www/armguard
# Domain: armguard.local

# Deploy second app (different Django project)
sudo bash deployment/deploy-other-app.sh
# Project dir: /var/www/otherapp
# Domain: otherapp.local
```

Each app gets:
- Its own virtual environment
- Its own Gunicorn service
- Its own Nginx site configuration
- Its own SSL certificate

---

## Manual Deployment (Alternative)

If you prefer step-by-step control, use the individual scripts:

```bash
# 1. Install Gunicorn service
sudo bash deployment/install-gunicorn-service.sh

# 2. Configure Nginx manually
sudo nano /etc/nginx/sites-available/armguard

# 3. Set up SSL manually
sudo bash deployment/setup-ssl-mkcert.sh
# or
sudo certbot --nginx -d yourdomain.com
```

See [README.md](README.md) for detailed manual instructions.

---

## Updating After Deployment

```bash
cd /var/www/armguard

# Pull latest changes
git pull

# Activate virtual environment
source .venv/bin/activate

# Install updated dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate --settings=core.settings_production

# Collect static files
python manage.py collectstatic --noinput --settings=core.settings_production

# Restart service
sudo systemctl restart gunicorn-armguard
```

Or use the automated update script (coming soon):
```bash
sudo bash deployment/update-armguard.sh
```

---

## Troubleshooting

### Script fails early
```bash
# Check error message
# Usually missing dependencies or permissions

# Try running with verbose output
sudo bash -x deployment/deploy-armguard.sh
```

### Service won't start
```bash
# Check logs
sudo journalctl -u gunicorn-armguard -n 50

# Common issues:
# - Missing environment variables
# - Database connection failed
# - Permission errors
```

### Can't connect to site
```bash
# Check firewall
sudo ufw status

# Check Nginx
sudo nginx -t
sudo systemctl status nginx

# Check if Gunicorn socket exists
ls -l /run/gunicorn-armguard.sock
```

### SSL certificate not trusted (mkcert)
```bash
# Copy CA certificate from server
scp user@server:~/.local/share/mkcert/rootCA.pem .

# Install on client:
# Windows: Double-click, Install Certificate, Trusted Root
# Mac: Double-click, Add to Keychain, Always Trust
# Linux: sudo cp rootCA.pem /usr/local/share/ca-certificates/mkcert.crt
#        sudo update-ca-certificates
```

---

## Uninstallation

```bash
# Stop and disable services
sudo systemctl stop gunicorn-armguard
sudo systemctl disable gunicorn-armguard

# Remove service file
sudo rm /etc/systemd/system/gunicorn-armguard.service
sudo systemctl daemon-reload

# Remove Nginx config
sudo rm /etc/nginx/sites-enabled/armguard
sudo rm /etc/nginx/sites-available/armguard
sudo systemctl reload nginx

# Remove application (CAUTION: Deletes all data!)
sudo rm -rf /var/www/armguard

# Remove logs
sudo rm -rf /var/log/armguard

# Remove database (if PostgreSQL)
sudo -u postgres psql -c "DROP DATABASE armguard_db;"
sudo -u postgres psql -c "DROP USER armguard_user;"
```

---

## Security Notes

### Default Security Measures Applied

✅ Django security features enabled
✅ HTTPS/SSL configured
✅ Firewall (UFW) configured
✅ Fail2Ban for brute-force protection
✅ Admin URL randomized
✅ Strong secrets generated
✅ Secure file permissions
✅ Security headers configured

### Additional Hardening (Optional)

For public deployments, consider:

1. **SSH Key-Only Authentication**
```bash
# Disable password authentication
sudo sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo systemctl restart sshd
```

2. **Change SSH Port**
```bash
sudo sed -i 's/#Port 22/Port 2222/' /etc/ssh/sshd_config
sudo ufw allow 2222/tcp
sudo ufw delete allow 22/tcp
sudo systemctl restart sshd
```

3. **Set Up Database Backups**
```bash
# Add to crontab
0 2 * * * /usr/bin/pg_dump armguard_db > /backup/armguard_$(date +\%Y\%m\%d).sql
```

4. **Configure Monitoring**
- Use [Uptime Kuma](https://github.com/louislam/uptime-kuma)
- Set up Prometheus + Grafana
- Configure log aggregation

See [SECURITY_ONLINE_TESTING.md](../SECURITY_ONLINE_TESTING.md) for complete hardening guide.

---

## Support

- **Documentation:** See `deployment/README.md` for detailed service management
- **Security:** See `SECURITY_ONLINE_TESTING.md` for hardening guide
- **Issues:** Check logs in `/var/log/armguard/`

---

## Quick Reference Card

```bash
# Deploy
sudo bash deployment/deploy-armguard.sh

# Check status
sudo systemctl status gunicorn-armguard

# View logs
sudo journalctl -u gunicorn-armguard -f

# Restart after changes
sudo systemctl restart gunicorn-armguard

# Update application
cd /var/www/armguard && git pull
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate --settings=core.settings_production
sudo systemctl restart gunicorn-armguard

# View deployment info
sudo cat /var/www/armguard/DEPLOYMENT_INFO.txt
```

---

**That's it! Your ArmGuard instance should now be running securely. 🚀**
