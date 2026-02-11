# Server Update Guide

## Quick Update (Automated)

### For Windows (PowerShell):
```powershell
cd c:\Users\9533RDS\Desktop\ARMGUARD_RDS_v.2\armguard
.\update-server.ps1
```

### For Linux/WSL/Git Bash:
```bash
cd /path/to/ARMGUARD_RDS_v.2/armguard
bash update-server.sh
```

---

## What the Update Script Does

1. ✅ **Tests SSH Connection** - Verifies you can connect to the server
2. 📦 **Creates Backup** - Saves current version before updating
3. 📥 **Pulls Latest Code** - Gets changes from GitHub
4. 🐍 **Updates Dependencies** - Installs/updates Python packages
5. 🗄️ **Runs Migrations** - Updates database schema if needed
6. 📁 **Collects Static Files** - Updates CSS, JS, images
7. 🔄 **Restarts Services** - Applies changes by restarting Gunicorn & Nginx
8. ✅ **Verifies Status** - Shows service status and recent commits

---

## Configuration

You can customize the update script by setting environment variables:

### PowerShell:
```powershell
$env:SERVER_IP = "192.168.0.1"      # Your server IP
$env:SSH_USER = "rds"                # SSH username
$env:PROJECT_DIR = "/var/www/armguard"  # Project directory on server
```

### Bash:
```bash
export SERVER_IP="192.168.0.1"
export SSH_USER="rds"
export PROJECT_DIR="/var/www/armguard"
```

---

## Manual Update Process

If you prefer to update manually via SSH:

```bash
# 1. SSH into the server
ssh rds@192.168.0.1

# 2. Navigate to project
cd /var/www/armguard

# 3. Pull latest changes
git pull origin main

# 4. Activate virtual environment
source venv/bin/activate

# 5. Update dependencies
pip install -r requirements.txt --upgrade

# 6. Run migrations
python manage.py migrate

# 7. Collect static files
python manage.py collectstatic --noinput

# 8. Restart services
sudo systemctl restart armguard
sudo systemctl restart nginx

# 9. Check status
sudo systemctl status armguard
```

---

## Troubleshooting

### SSH Connection Failed

**Problem:** Cannot connect to server via SSH

**Solutions:**
1. Check if SSH is enabled on the server:
   - See [SSH_SETUP_GUIDE.md](SSH_SETUP_GUIDE.md) for detailed instructions
   
2. Verify server IP:
   ```powershell
   Test-NetConnection 192.168.0.1 -Port 22
   ```

3. Test manual SSH:
   ```bash
   ssh rds@192.168.0.1
   ```

### Git Pull Failed

**Problem:** Git pull errors or conflicts

**Solutions:**
1. SSH into server and check status:
   ```bash
   cd /var/www/armguard
   git status
   git log --oneline -5
   ```

2. If there are conflicts, stash local changes:
   ```bash
   git stash
   git pull origin main
   git stash pop
   ```

3. Or reset to remote (CAUTION: loses local changes):
   ```bash
   git fetch origin
   git reset --hard origin/main
   ```

### Service Restart Failed

**Problem:** Services won't restart

**Solutions:**
1. Check service name:
   ```bash
   sudo systemctl list-units | grep -E 'armguard|gunicorn'
   ```

2. Check service logs:
   ```bash
   sudo journalctl -u armguard -n 50
   sudo journalctl -u nginx -n 50
   ```

3. Manual restart with different names:
   ```bash
   sudo systemctl restart gunicorn
   sudo systemctl restart armguard-gunicorn
   sudo systemctl restart daphne  # if using WebSockets
   ```

### Virtual Environment Not Found

**Problem:** Cannot activate virtual environment

**Solution:**
1. Check if venv exists:
   ```bash
   ls -la /var/www/armguard/venv
   ```

2. Create if missing:
   ```bash
   cd /var/www/armguard
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

---

## Rollback Procedure

If the update causes issues, you can rollback:

### Using Git:
```bash
# SSH to server
ssh rds@192.168.0.1

# Navigate to project
cd /var/www/armguard

# View recent commits
git log --oneline -10

# Rollback to previous commit (replace COMMIT_HASH)
git reset --hard COMMIT_HASH

# Restart services
sudo systemctl restart armguard nginx
```

### Using Backup:
```bash
# List backups
ls -la /var/www/armguard/backups/

# Restore from backup (replace with your backup date)
cd /var/www/armguard
cp -r backups/backup_20260210_120000/* .

# Restart services
sudo systemctl restart armguard nginx
```

---

## Post-Update Verification

After updating, verify everything works:

1. **Check Service Status:**
   ```bash
   sudo systemctl status armguard
   sudo systemctl status nginx
   ```

2. **Test Web Access:**
   - Open browser: `http://192.168.0.1` or `https://armguard.local`
   - Login and test key features

3. **Check Logs:**
   ```bash
   tail -f /var/log/nginx/error.log
   sudo journalctl -u armguard -f
   ```

4. **Test Database:**
   ```bash
   cd /var/www/armguard
   source venv/bin/activate
   python manage.py shell
   >>> from personnel.models import Personnel
   >>> Personnel.objects.count()
   ```

---

## Quick Reference Commands

```powershell
# Update server (PowerShell)
.\update-server.ps1

# SSH to server
ssh rds@192.168.0.1

# Check server port
Test-NetConnection 192.168.0.1 -Port 22

# View deployment logs
ssh rds@192.168.0.1 'sudo journalctl -u armguard -n 100'

# Restart services remotely
ssh rds@192.168.0.1 'sudo systemctl restart armguard nginx'
```

---

## First-Time Server Setup

If this is your first time deploying to the server:

1. **Clone repository on server:**
   ```bash
   ssh rds@192.168.0.1
   cd /var/www
   sudo git clone https://github.com/Stealth3535/ARMGUARD_RDS_v.2.git armguard
   ```

2. **Run full deployment:**
   ```bash
   cd /var/www/armguard/deployment_A/methods/production
   sudo bash deploy-armguard.sh
   ```

3. **Then use update script for future updates**

---

## Security Notes

- ✅ Backups are created before each update
- ✅ Database migrations are run automatically
- ✅ Static files are collected with `--noinput` flag
- ✅ Services are restarted to apply changes
- ⚠️ Ensure your SSH key is secure and password-protected
- ⚠️ Only run updates during maintenance windows for production systems

---

## Support

For detailed deployment documentation, see:
- [docs/installation.md](../docs/installation.md)
- [docs/deployment.md](../docs/deployment.md) (coming soon)
- [SSH_SETUP_GUIDE.md](SSH_SETUP_GUIDE.md)
- [deployment_A/DEVICE_AUTHORIZATION_GUIDE.md](deployment_A/DEVICE_AUTHORIZATION_GUIDE.md)
