# Quick Production Deployment Guide

## 🚀 NEW: Auto-Detection Feature

The deployment scripts now **automatically detect** if you're running from within a cloned repository and offer to use that location instead of copying files!

---

## ✨ How It Works

### 1. **Auto-Detection** (New!)
When you run the deployment from within your cloned repo:

```bash
cd ~/ARMGUARD_RDS_v.2/armguard/deployment_A
sudo bash ubuntu-deploy.sh --production
```

The script will:
- ✅ **Detect** your project at `~/ARMGUARD_RDS_v.2/armguard`
- ✅ **Offer to use** the existing location (recommended for git repos)
- ✅ **Show you** the benefits of each option:
  - **Use existing:** Easy updates with `git pull`
  - **Copy to /var/www:** Separate production from development

### 2. **Smart Prompts**
You'll see:

```
📦 Project auto-detected at: /home/rds/ARMGUARD_RDS_v.2/armguard
   Git repository detected

Option 1: Use existing repository location
   Path: /home/rds/ARMGUARD_RDS_v.2/armguard
   Benefits: Easy updates with 'git pull'

Option 2: Copy to deployment directory  
   Path: /var/www/armguard
   Benefits: Separate from development

Use existing location? [Y/n]:
```

**Just press ENTER** to use your existing repo location!

---

## 📋 Deployment Methods

### **Method 1: Ubuntu-Optimized Deployment (RECOMMENDED)**

```bash
cd ~/ARMGUARD_RDS_v.2/armguard/deployment_A

# For production with Let's Encrypt SSL
sudo bash ubuntu-deploy.sh --production

# For LAN-only deployment with mkcert
sudo bash ubuntu-deploy.sh --quick
```

**Features:**
- ✅ Auto-detects your hardware (Ubuntu server, Raspberry Pi, HP ProDesk, etc.)
- ✅ Optimizes workers based on CPU/RAM
- ✅ Auto-detects project location
- ✅ Chooses best database (PostgreSQL vs SQLite)

---

### **Method 2: Direct Production Deployment**

```bash
cd ~/ARMGUARD_RDS_v.2/armguard/deployment_A/methods/production
sudo bash deploy-armguard.sh
```

**Features:**
- ✅ Full control over configuration
- ✅ Auto-detects project location
- ✅ Offers to use existing git repo

---

### **Method 3: Modular Step-by-Step**

```bash
cd ~/ARMGUARD_RDS_v.2/armguard/deployment_A

sudo bash 01_setup.sh      # Install dependencies
sudo bash 02_config.sh     # Configure SSL & Django
sudo bash 03_services.sh   # Setup services
sudo bash 04_monitoring.sh # Enable monitoring
```

**Features:**
- ✅ Run individual steps
- ✅ Resume from any point
- ✅ Better error recovery

---

## 🎯 Recommended Workflow

### First-Time Production Deployment

```bash
# 1. Navigate to your cloned repo
cd ~/ARMGUARD_RDS_v.2/armguard/deployment_A

# 2. Run Ubuntu-optimized deployment
sudo bash ubuntu-deploy.sh --production

# 3. When prompted, choose to use existing location [Y]
#    This keeps your git repo active for easy updates

# Configuration will be:
#   - Project: /home/rds/ARMGUARD_RDS_v.2/armguard
#   - Database: PostgreSQL (optimized for your RAM)
#   - SSL: Let's Encrypt (for production)
#   - Workers: Optimized for your CPU cores
#   - Firewall: Enabled with UFW
```

### Future Updates

```bash
# 1. Pull latest code
cd ~/ARMGUARD_RDS_v.2
git pull origin main

# 2. Update dependencies and restart
cd armguard
source .venv/bin/activate
pip install -r requirements.txt --upgrade
python manage.py migrate
python manage.py collectstatic --noinput

# 3. Restart services
sudo systemctl restart gunicorn-armguard
sudo systemctl restart nginx
```

---

## ⚙️ Configuration Options

### Ubuntu Deploy Script Options

```bash
sudo bash ubuntu-deploy.sh [OPTIONS]

Options:
  --quick       Quick LAN deployment (mkcert SSL)
  --production  Full production (Let's Encrypt SSL)
  --lan         LAN-only deployment
  --wan         Internet-facing
  --hybrid      Mixed LAN/WAN
```

### Environment Variables

You can set these before running:

```bash
export PROJECT_DIR="/home/rds/ARMGUARD_RDS_v.2/armguard"
export DOMAIN="armguard.yourdomain.com"
export NETWORK_TYPE="lan"

sudo -E bash ubuntu-deploy.sh --production
```

---

## 🔧 Manual Project Path

If auto-detection doesn't work or you want to specify manually:

### During Configuration

When prompted for "Project directory", enter:
```
/home/rds/ARMGUARD_RDS_v.2/armguard
```

### Via Environment Variable

```bash
sudo PROJECT_DIR="/home/rds/ARMGUARD_RDS_v.2/armguard" bash deploy-armguard.sh
```

---

## 📊 Post-Deployment

### Check Status

```bash
# Service status
sudo systemctl status gunicorn-armguard
sudo systemctl status nginx
sudo systemctl status redis-server
sudo systemctl status postgresql

# Health check
cd ~/ARMGUARD_RDS_v.2/armguard/deployment_A/methods/production
sudo bash health-check.sh
```

### Access Your Application

```bash
# Get your server IP
hostname -I

# Access via browser
https://192.168.0.10  # Your server IP
https://armguard.local
```

### View Logs

```bash
# Application logs
sudo journalctl -u gunicorn-armguard -f

# Nginx logs
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log

# Database logs (if PostgreSQL)
sudo journalctl -u postgresql -f
```

---

## 🐛 Troubleshooting

### Project Not Detected

If the script doesn't auto-detect your project:

```bash
# Verify manage.py location
ls -la ~/ARMGUARD_RDS_v.2/armguard/manage.py

# Run from correct directory
cd ~/ARMGUARD_RDS_v.2/armguard/deployment_A
pwd  # Should show: /home/rds/ARMGUARD_RDS_v.2/armguard/deployment_A
```

### Want to Copy Instead of Using Existing

When prompted "Use existing location?", type **n** to copy to `/var/www/armguard` instead.

### Change Project Location After Deployment

```bash
# Edit service file
sudo nano /etc/systemd/system/gunicorn-armguard.service

# Update WorkingDirectory and paths
# Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart gunicorn-armguard
```

---

## 💡 Tips

1. **Use existing location** if you want easy updates with `git pull`
2. **Copy to /var/www** if you want production separate from development
3. **Always run from deployment_A folder** for best auto-detection
4. **Use ubuntu-deploy.sh** for automatic hardware optimization
5. **Check health-check.sh** after deployment to verify everything works

---

## 🔒 Security Notes

- ✅ Deployment creates strong database passwords automatically
- ✅ UFW firewall is configured with proper rules
- ✅ SSL certificates are auto-generated (mkcert or Let's Encrypt)
- ✅ Django SECRET_KEY is generated uniquely
- ✅ Admin URL is randomized for security
- ✅ Fail2ban is configured for brute-force protection

---

## 📚 Additional Resources

- [UBUNTU_DEPLOYMENT_GUIDE.md](UBUNTU_DEPLOYMENT_GUIDE.md) - Detailed Ubuntu guide
- [DEVICE_AUTHORIZATION_GUIDE.md](DEVICE_AUTHORIZATION_GUIDE.md) - Device security
- [README.md](README.md) - Complete deployment documentation
- [methods/production/](methods/production/) - Individual deployment scripts
