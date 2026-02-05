# 🎯 ArmGuard System Operations Manual

## 📋 Daily Operations & Maintenance Guide

### 🚀 System Access

**Your ArmGuard system is deployed at:**
- **Local Network**: `http://192.168.0.177`
- **Admin Panel**: `http://192.168.0.177/admin`
- **VPN Access**: `http://10.0.0.1` (through VPN)

### 🔧 Service Management

#### Check System Status
```bash
# Check all services
sudo systemctl status armguard nginx postgresql

# Quick health check
curl -I http://localhost
```

#### Restart Services
```bash
# Restart ArmGuard application
sudo systemctl restart armguard

# Restart web server
sudo systemctl restart nginx

# Restart database
sudo systemctl restart postgresql

# Restart all
sudo systemctl restart armguard nginx postgresql
```

#### View Logs
```bash
# ArmGuard application logs
sudo journalctl -u armguard -f

# Nginx access/error logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# System logs
sudo tail -f /var/log/syslog
```

### 🔐 VPN Client Management

#### Generate New VPN Clients
```bash
cd /home/armguard/armguard/deployment

# Generate clients for different roles
sudo ./rpi4b-generate-client.sh john-smith commander
sudo ./rpi4b-generate-client.sh jane-doe armorer
sudo ./rpi4b-generate-client.sh emergency-ops emergency
sudo ./rpi4b-generate-client.sh regular-user personnel
```

#### VPN Status and Management
```bash
# Check VPN status
sudo wg show

# Restart VPN server
sudo systemctl restart wg-quick@wg0

# View VPN logs
sudo journalctl -u wg-quick@wg0 -f
```

#### Access Control by Role
| Role | Permissions | VPN Access |
|------|-------------|------------|
| **Commander** | Full system access, all reports | Full network access |
| **Armorer** | Equipment inventory, maintenance | Limited network access |
| **Emergency** | Critical equipment only | Restricted access |
| **Personnel** | Personal status only | Minimal access |

### 🗄️ Database Management

#### Database Backup
```bash
# Create database backup
sudo -u postgres pg_dump armguard > /opt/armguard/backups/armguard-$(date +%Y%m%d).sql

# Create compressed backup
sudo -u postgres pg_dump armguard | gzip > /opt/armguard/backups/armguard-$(date +%Y%m%d).sql.gz
```

#### Database Restore
```bash
# Restore from backup
sudo -u postgres psql armguard < /opt/armguard/backups/armguard-YYYYMMDD.sql
```

#### Database Maintenance
```bash
# Access Django admin shell
cd /opt/armguard
source venv/bin/activate
python manage.py shell

# Run database migrations (after updates)
python manage.py migrate

# Create new admin user
python manage.py createsuperuser
```

### 🔄 System Updates

#### Update ArmGuard Application
```bash
# If using git
cd /home/armguard/armguard
git pull

# Copy to production directory
sudo cp -r /home/armguard/armguard/* /opt/armguard/

# Install new dependencies (if any)
cd /opt/armguard
source venv/bin/activate
pip install -r requirements.txt

# Run migrations
python manage.py migrate
python manage.py collectstatic --noinput

# Restart services
sudo systemctl restart armguard nginx
```

#### System Security Updates
```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Reboot if kernel updates
sudo reboot
```

### 📊 Monitoring & Troubleshooting

#### Performance Monitoring
```bash
# Check CPU/Memory usage
htop

# Check disk space
df -h

# Check network connections
sudo netstat -tlnp

# Check service resource usage
sudo systemctl status armguard --no-pager -l
```

#### Common Issues & Solutions

**Service Won't Start:**
```bash
# Check logs
sudo journalctl -u armguard -n 50

# Check file permissions
sudo chown -R www-data:www-data /opt/armguard
sudo chmod -R 755 /opt/armguard

# Restart service
sudo systemctl restart armguard
```

**Database Connection Issues:**
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Test database connection
sudo -u postgres psql -c "SELECT version();"

# Check database user
sudo -u postgres psql -c "\du"
```

**Web Server Issues:**
```bash
# Test Nginx configuration
sudo nginx -t

# Check if port 80 is available
sudo netstat -tlnp | grep :80

# Check firewall
sudo ufw status
```

**VPN Issues:**
```bash
# Check WireGuard status
sudo wg show

# Check firewall for VPN port
sudo ufw status | grep 51820

# Restart VPN
sudo systemctl restart wg-quick@wg0
```

### 🔒 Security Best Practices

#### Regular Security Tasks
- Change default passwords monthly
- Review VPN client access quarterly
- Monitor system logs daily
- Update system packages weekly
- Backup database weekly

#### Security Monitoring
```bash
# Check failed login attempts
sudo grep "Failed password" /var/log/auth.log

# Check active VPN connections
sudo wg show

# Monitor system resources
sudo iotop
sudo nethogs
```

### 📱 Mobile & Remote Access

#### For Remote Users
1. **Install WireGuard client** on device
2. **Import VPN configuration** or scan QR code
3. **Connect to VPN**
4. **Access**: `http://10.0.0.1`

#### Network Requirements
- **LAN Access**: Full functionality (transactions, management)
- **VPN Access**: Read-only status, reports (security compliant)
- **Internet Access**: Blocked (security policy)

### 🆘 Emergency Procedures

#### Service Recovery
```bash
# Emergency restart all services
sudo systemctl restart armguard nginx postgresql wg-quick@wg0

# If database is corrupted
sudo systemctl stop armguard
# Restore from backup
sudo systemctl start armguard
```

#### Contact Information
- **System Admin**: [Your contact info]
- **Network Admin**: [Network admin contact]
- **Emergency Contact**: [24/7 support contact]

---

*Operations Manual - Last Updated: February 3, 2026*