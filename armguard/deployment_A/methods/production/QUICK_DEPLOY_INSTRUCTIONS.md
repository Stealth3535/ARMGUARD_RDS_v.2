# Quick Deployment Instructions

## 🚨 **IMPORTANT: Pull Latest Changes First!**

```bash
# Step 1: Pull the latest changes
cd ~/ARMGUARD_RDS_v.2/armguard
git pull origin main

# Step 2: Run the deployment script
cd deployment_A/methods/production
sudo bash deploy-armguard.sh
```

## ✅ **Correct Configuration to Use:**

When prompted, use these values:

```
Project directory: [/home/rds/ARMGUARD_RDS_v.2/armguard]  ← Press ENTER
Domain name: [armguard.local]  ← Or your domain
Server IP: [auto-detected]  ← Press ENTER
Run as user: [rds]  ← Press ENTER (NOT www-data!)
Run as group: [rds]  ← Press ENTER (NOT www-data!)
```

## 🔧 **Clean Up Failed Deployment:**

If you need to clean up from the failed attempt:

```bash
# Stop and remove failed service
sudo systemctl stop gunicorn-armguard 2>/dev/null || true
sudo systemctl disable gunicorn-armguard 2>/dev/null || true

# Remove service file
sudo rm -f /etc/systemd/system/gunicorn-armguard.service

# Reload systemd
sudo systemctl daemon-reload

# Remove any files created in wrong location
sudo rm -rf /var/www/armguard 2>/dev/null || true
```

## 🚀 **OR Use Quick Fix Script (Faster!):**

Instead of re-running the full deployment, use the quick fix:

```bash
cd ~/ARMGUARD_RDS_v.2/armguard
git pull origin main

cd deployment_A/methods/production
chmod +x quick-fix-use-cloned-repo.sh
sudo bash quick-fix-use-cloned-repo.sh
```

This will:
- ✅ Use correct paths automatically
- ✅ Use rds user (no prompts)
- ✅ Fix permissions
- ✅ Start service
- ✅ Verify everything works

**Estimated time: 2-3 minutes**
