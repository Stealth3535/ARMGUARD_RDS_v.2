# 🌐 Nginx & SSL Installation Guide for ArmGuard

Complete guide for setting up Nginx web server and SSL/TLS certificates on Raspberry Pi 5.

---

## 📋 Overview

This guide covers:
1. **Nginx Installation** - Web server and reverse proxy
2. **SSL/TLS Setup** - HTTPS with mkcert (local development)
3. **Production SSL** - Let's Encrypt for public deployment

---

## 🚀 Quick Start

### Step 1: Install Nginx
```bash
cd /var/www/armguard
sudo bash deployment/install-nginx.sh
```

**What it does:**
- ✅ Installs Nginx web server
- ✅ Configures reverse proxy to Gunicorn
- ✅ Sets up static/media file serving
- ✅ Adds security headers
- ✅ Configures firewall rules

**Default access:** `http://your-server-ip`

### Step 2: Install SSL/HTTPS (Optional)
```bash
cd /var/www/armguard
sudo bash deployment/install-mkcert-ssl.sh
```

**What it does:**
- ✅ Installs mkcert certificate tool
- ✅ Generates self-signed SSL certificates
- ✅ Configures Nginx for HTTPS
- ✅ Enables HTTP → HTTPS redirect
- ✅ Adds SSL security headers

**HTTPS access:** `https://your-server-ip`

---

## 📖 Detailed Instructions

### Nginx Installation

#### Prerequisites
- Ubuntu Server installed on Raspberry Pi 5
- ArmGuard application deployed
- Gunicorn service running

#### Installation Steps

1. **Navigate to deployment directory:**
   ```bash
   cd /var/www/armguard/deployment
   ```

2. **Run Nginx installer:**
   ```bash
   sudo bash install-nginx.sh
   ```

3. **Optional - Custom domain:**
   ```bash
   sudo bash install-nginx.sh armguard.local
   ```

#### What Gets Configured

**Nginx Configuration File:** `/etc/nginx/sites-available/armguard`

```nginx
# Upstream to Gunicorn
upstream armguard_app {
    server unix:/var/www/armguard/gunicorn.sock;
}

# HTTP Server
server {
    listen 80;
    server_name your-ip armguard.local;
    
    # Static files
    location /static/ {
        alias /var/www/armguard/staticfiles/;
    }
    
    # Media files
    location /media/ {
        alias /var/www/armguard/core/media/;
    }
    
    # Proxy to Gunicorn
    location / {
        proxy_pass http://armguard_app;
    }
}
```

**Log Files:**
- Access: `/var/log/nginx/armguard_access.log`
- Errors: `/var/log/nginx/armguard_error.log`

#### Verification

```bash
# Check Nginx status
sudo systemctl status nginx

# Test configuration
sudo nginx -t

# View logs
sudo tail -f /var/log/nginx/armguard_error.log
```

---

### SSL/TLS Installation (mkcert)

#### When to Use
- ✅ Local development
- ✅ Internal network testing
- ✅ Mobile device testing (requires CA import)

#### When NOT to Use
- ❌ Public-facing production servers (use Let's Encrypt instead)
- ❌ Servers accessible from internet

#### Installation Steps

1. **Install mkcert and generate certificates:**
   ```bash
   cd /var/www/armguard/deployment
   sudo bash install-mkcert-ssl.sh
   ```

2. **Optional - Custom domain:**
   ```bash
   sudo bash install-mkcert-ssl.sh armguard.local
   ```

#### Certificate Files

**Location:** `/etc/ssl/armguard/`
- `armguard-cert.pem` - Public certificate
- `armguard-key.pem` - Private key (chmod 600)

**Valid for:**
- Domain specified (default: armguard.local)
- localhost
- 127.0.0.1
- Your server IP
- ::1 (IPv6 localhost)

#### Trust the Certificate

**On the Server (already done):**
```bash
mkcert -install
```

**On Client Devices (Desktop/Laptop):**

1. Get CA certificate location:
   ```bash
   mkcert -CAROOT
   # Output: /root/.local/share/mkcert
   ```

2. Copy CA certificate:
   ```bash
   sudo cat $(mkcert -CAROOT)/rootCA.pem
   ```

3. Import to browser:
   - **Chrome/Edge:** Settings → Privacy & Security → Security → Manage Certificates
   - **Firefox:** Settings → Privacy & Security → Certificates → View Certificates → Import
   - **macOS:** Add to Keychain Access
   - **Windows:** Add to Trusted Root Certification Authorities

**On Mobile Devices (Android/iOS):**

1. Copy CA certificate to device:
   ```bash
   # On server
   sudo cat $(mkcert -CAROOT)/rootCA.pem > /tmp/armguard-ca.pem
   
   # Transfer to device (via email, USB, or network share)
   ```

2. Install certificate:
   - **Android:** Settings → Security → Install from storage → Select file
   - **iOS:** Settings → General → VPN & Device Management → Install Profile

#### Django SSL Configuration

After installing SSL, update `.env`:

```env
# SSL/HTTPS Settings
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_HSTS_SECONDS=31536000
```

Restart Gunicorn:
```bash
sudo systemctl restart gunicorn
```

---

## 🔐 Production SSL (Let's Encrypt)

For public-facing production servers, use Let's Encrypt (free, trusted by all browsers).

### Prerequisites
- Public domain name pointing to your server
- Ports 80 and 443 open on firewall
- Server accessible from internet

### Installation Steps

1. **Install Certbot:**
   ```bash
   sudo apt update
   sudo apt install -y certbot python3-certbot-nginx
   ```

2. **Generate certificate:**
   ```bash
   sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
   ```

3. **Answer prompts:**
   - Enter email address
   - Agree to Terms of Service
   - Choose redirect option (recommended: Yes)

4. **Auto-renewal (automatic):**
   ```bash
   # Certbot creates a systemd timer automatically
   sudo systemctl status certbot.timer
   
   # Test renewal
   sudo certbot renew --dry-run
   ```

### Certificate Files
- Location: `/etc/letsencrypt/live/yourdomain.com/`
- Auto-renewed every 60 days

---

## 🛠️ Troubleshooting

### Nginx Won't Start

**Check configuration:**
```bash
sudo nginx -t
```

**Check logs:**
```bash
sudo journalctl -u nginx -n 50
sudo tail -f /var/log/nginx/error.log
```

**Common issues:**
- Port 80/443 already in use
- Permission denied on socket file
- Invalid configuration syntax

### 502 Bad Gateway

**Causes:**
- Gunicorn not running
- Socket file permissions
- Gunicorn socket path mismatch

**Fix:**
```bash
# Check Gunicorn status
sudo systemctl status gunicorn

# Restart Gunicorn
sudo systemctl restart gunicorn

# Check socket file exists
ls -la /var/www/armguard/gunicorn.sock

# Fix permissions
sudo chown www-data:www-data /var/www/armguard/gunicorn.sock
```

### SSL Certificate Not Trusted

**For mkcert:**
- Install CA certificate on client device
- Clear browser cache
- Restart browser

**For Let's Encrypt:**
- Ensure domain points to server
- Check firewall allows port 80/443
- Run: `sudo certbot certificates`

### Static Files Not Loading

**Check configuration:**
```bash
# Verify static files exist
ls -la /var/www/armguard/staticfiles/

# Re-collect static files
cd /var/www/armguard
python manage.py collectstatic --noinput

# Check Nginx config
sudo nginx -t
```

---

## 📊 Performance Tuning

### Nginx Optimization

**Edit:** `/etc/nginx/nginx.conf`

```nginx
user www-data;
worker_processes auto;  # Use all CPU cores
worker_connections 1024;

# Enable gzip compression
gzip on;
gzip_vary on;
gzip_min_length 1000;
gzip_types text/plain text/css application/json application/javascript text/xml application/xml;

# Buffer sizes
client_body_buffer_size 16K;
client_header_buffer_size 1k;
large_client_header_buffers 4 8k;

# Timeouts
client_body_timeout 12;
client_header_timeout 12;
keepalive_timeout 15;
send_timeout 10;
```

### Static File Caching

Already configured in `install-nginx.sh`:
- Static files: 30 days cache
- Media files: 7 days cache

---

## 🔍 Verification Commands

### Check All Services

```bash
# Nginx status
sudo systemctl status nginx

# Gunicorn status
sudo systemctl status gunicorn

# Test HTTP
curl -I http://localhost

# Test HTTPS (if SSL installed)
curl -I https://localhost

# Check certificates
sudo ls -la /etc/ssl/armguard/
```

### Monitor Logs

```bash
# Nginx access log
sudo tail -f /var/log/nginx/armguard_access.log

# Nginx error log
sudo tail -f /var/log/nginx/armguard_error.log

# Gunicorn log
sudo journalctl -u gunicorn -f
```

---

## 📁 File Structure

```
/etc/nginx/
├── sites-available/
│   └── armguard              # Main config
└── sites-enabled/
    └── armguard -> ../sites-available/armguard

/etc/ssl/armguard/            # SSL certificates (if mkcert)
├── armguard-cert.pem
└── armguard-key.pem

/var/log/nginx/
├── armguard_access.log
└── armguard_error.log

/var/www/armguard/
├── gunicorn.sock             # Unix socket for Gunicorn
├── staticfiles/              # Served by Nginx
└── core/media/               # Served by Nginx
```

---

## 🎯 Quick Reference

### Common Commands

```bash
# Restart Nginx
sudo systemctl restart nginx

# Reload Nginx (no downtime)
sudo systemctl reload nginx

# Test configuration
sudo nginx -t

# View Nginx status
sudo systemctl status nginx

# Enable Nginx on boot
sudo systemctl enable nginx

# View real-time access logs
sudo tail -f /var/log/nginx/armguard_access.log

# Check open ports
sudo netstat -tulpn | grep nginx
```

### Ports
- **HTTP:** 80
- **HTTPS:** 443

### URLs
- **HTTP:** `http://your-server-ip`
- **HTTPS:** `https://your-server-ip` (after SSL setup)
- **Custom domain:** `http://armguard.local` or `https://armguard.local`

---

## ✅ Post-Installation Checklist

- [ ] Nginx installed and running
- [ ] Can access application via HTTP
- [ ] Static files loading correctly
- [ ] Media files (QR codes, images) loading
- [ ] SSL certificate installed (optional)
- [ ] Can access application via HTTPS (if SSL enabled)
- [ ] HTTP redirects to HTTPS (if SSL enabled)
- [ ] Django .env configured for SSL (if SSL enabled)
- [ ] Firewall rules configured
- [ ] Client devices trust certificate (if mkcert SSL)

---

## 🆘 Support

If you encounter issues:

1. Check logs: `/var/log/nginx/armguard_error.log`
2. Test configuration: `sudo nginx -t`
3. Verify Gunicorn: `sudo systemctl status gunicorn`
4. Review this guide's troubleshooting section

---

**Scripts Location:** `/var/www/armguard/deployment/`
- `install-nginx.sh` - Nginx installation
- `install-mkcert-ssl.sh` - SSL/TLS setup
