# 🚀 ArmGuard Deployment v2.0 - Quick Reference Card

## 📋 New Commands at a Glance

### Health & Monitoring
```bash
# Check system health
sudo bash deployment/health-check.sh

# Detect platform and get optimization tips
bash deployment/detect-environment.sh

# View logs in real-time
sudo tail -f /var/log/armguard/error.log
sudo journalctl -u gunicorn-armguard -f
```

### Backup & Recovery
```bash
# List available backups
ls -lh /var/www/armguard/backups/

# Rollback to previous version (interactive)
sudo bash deployment/rollback.sh

# Rollback to specific backup
sudo bash deployment/rollback.sh /path/to/backup_file
```

### Deployment & Updates
```bash
# Deploy with new security features
sudo bash deployment/install-nginx-enhanced.sh

# Update with automatic health check
sudo bash deployment/update-armguard.sh
# → Backup → Update → Health Check → Auto-rollback if failed

# Set up log rotation
sudo bash deployment/setup-logrotate.sh
```

## 🔧 Configuration Quick Tips

### Environment Variables (add to .env or config.sh)
```bash
# Performance Tuning
export ARMGUARD_WORKERS=5              # Number of Gunicorn workers
export ARMGUARD_TIMEOUT=60             # Request timeout (seconds)
export ARMGUARD_MAX_REQUESTS=1000      # Max requests per worker

# Security Tuning
export ARMGUARD_RATE_LIMIT="10r/s"     # Rate limit
export ARMGUARD_CLIENT_MAX_BODY_SIZE="10M"  # Upload limit

# Custom Paths
export ARMGUARD_PROJECT_DIR="/custom/path"
export ARMGUARD_SOCKET_PATH="/custom/socket"
```

### Platform-Specific Recommendations
```bash
# Raspberry Pi (Low Memory)
export ARMGUARD_WORKERS=3
export ARMGUARD_TIMEOUT=90

# High-Traffic Server
export ARMGUARD_WORKERS=9
export ARMGUARD_RATE_LIMIT="30r/s"

# Development
export ARMGUARD_WORKERS=2
export ARMGUARD_RATE_LIMIT="100r/s"
```

## 🛡️ Security Features (v2.0)

### Rate Limits (Nginx Enhanced)
| Endpoint | Limit | Burst |
|----------|-------|-------|
| General pages | 10 req/s | 20 |
| Login/Auth | 5 req/min | 3 |
| API | 20 req/s | 10 |
| Admin | 5 req/min | 5 |

### Additional Security
- ✅ Connection limit: 10 per IP
- ✅ XSS/CSRF protection headers
- ✅ PHP/ASP exploit blocking
- ✅ Hidden file protection

## 📊 Health Check Categories

1. **System Health** - CPU, memory, disk usage
2. **Service Status** - Gunicorn, Nginx running
3. **Network** - Ports, HTTP/HTTPS connectivity
4. **Application** - Files, database, static files
5. **Logs** - Recent errors detection
6. **Security** - Firewall, permissions

**Exit Codes:**
- `0` = Healthy or warnings only
- `1` = Critical failures

## 🔄 Update Workflow (Enhanced)

```
sudo bash deployment/update-armguard.sh
    ↓
1. Pre-update checks
2. Automatic backup
3. Pull latest code
4. Install dependencies
5. Run migrations
6. Collect static files
7. Restart services
8. 🆕 Health check
9. 🆕 Auto-rollback option (if failed)
    ↓
Success! ✅
```

## 🆘 Troubleshooting Quick Fixes

### Health Check Failed
```bash
# Get detailed report
sudo bash deployment/health-check.sh

# Check service logs
sudo journalctl -u gunicorn-armguard -n 50

# Restart service
sudo systemctl restart gunicorn-armguard
```

### Need to Rollback
```bash
# Interactive selection
sudo bash deployment/rollback.sh

# Or specify backup directly
sudo bash deployment/rollback.sh /var/www/armguard/backups/db.sqlite3.backup_YYYYMMDD_HHMMSS
```

### High CPU/Memory
```bash
# Check current usage
free -h
top -bn1 | head -20

# Reduce workers
export ARMGUARD_WORKERS=3
sudo systemctl restart gunicorn-armguard
```

### Rate Limiting Too Strict
```bash
# Edit Nginx config
sudo nano /etc/nginx/sites-available/armguard

# Find and adjust:
# limit_req_zone ... rate=20r/s;  # Increase rate

# Test and reload
sudo nginx -t
sudo systemctl reload nginx
```

### Logs Growing Too Large
```bash
# Check log sizes
du -sh /var/log/armguard/*
du -sh /var/log/nginx/armguard_*

# Setup log rotation (if not done)
sudo bash deployment/setup-logrotate.sh

# Force rotation now
sudo logrotate -f /etc/logrotate.d/armguard
```

## 📁 Key File Locations

```
/var/www/armguard/              # Application directory
/var/www/armguard/backups/      # Database backups
/var/log/armguard/              # Application logs
/var/log/nginx/armguard_*.log   # Nginx logs
/etc/nginx/sites-available/armguard  # Nginx config
/etc/systemd/system/gunicorn-armguard.service  # Service file
/etc/logrotate.d/armguard       # Log rotation config
/run/gunicorn-armguard.sock     # Unix socket
```

## 🎯 Common Tasks

### Daily Monitoring
```bash
# Morning health check
sudo bash deployment/health-check.sh

# Check logs for errors
sudo grep -i error /var/log/armguard/error.log | tail -20

# Check disk space
df -h /
```

### Weekly Maintenance
```bash
# List and verify backups
ls -lh /var/www/armguard/backups/

# Check log rotation
ls -lh /var/log/armguard/

# Update application
sudo bash deployment/update-armguard.sh
```

### Monthly Tasks
```bash
# Full system check
bash deployment/detect-environment.sh
sudo bash deployment/health-check.sh

# Review rate limiting effectiveness
sudo grep "limiting requests" /var/log/nginx/armguard_error.log | wc -l

# Clean old backups (keeps last 5 automatically)
ls -t /var/www/armguard/backups/ | tail -n +6
```

## 📞 Getting Help

### Documentation Files
- `README.md` - Complete script reference
- `UPGRADE_GUIDE_V2.md` - Detailed upgrade instructions
- `V2_UPGRADE_SUMMARY.md` - Feature comparison
- `QUICK_DEPLOY.md` - Fast deployment guide
- `NGINX_SSL_GUIDE.md` - SSL/HTTPS setup

### Diagnostic Commands
```bash
# Service status
sudo systemctl status gunicorn-armguard
sudo systemctl status nginx

# Recent logs
sudo journalctl -u gunicorn-armguard -n 100
sudo tail -100 /var/log/nginx/armguard_error.log

# Configuration test
sudo nginx -t
python manage.py check

# Network test
curl -I http://localhost
netstat -tuln | grep -E '80|443|8000'
```

## 🎉 Quick Win Checklist

After installing v2.0, run these for instant benefits:

- [ ] `sudo bash deployment/health-check.sh` - Verify system health
- [ ] `sudo bash deployment/setup-logrotate.sh` - Never worry about logs
- [ ] `sudo bash deployment/install-nginx-enhanced.sh` - Boost security
- [ ] `ls /var/www/armguard/backups/` - Confirm backups exist
- [ ] `bash deployment/detect-environment.sh` - Optimize for your platform

---

**Print this card and keep it handy! 📄**
