# ArmGuard RPi Deployment - Quick Fix Guide

## Problem Summary
The deployment script creates a systemd socket unit (`armguard.socket`) that conflicts with Gunicorn's socket binding, causing the service to fail with:
```
[ERROR] Can't connect to /run/armguard.sock
```

## Solution: One-Command Fix

After running the standard deployment, execute this fix script:

```bash
curl -sSL "https://raw.githubusercontent.com/Stealth3535/ARMGUARD_RDS/main/armguard/deployment/fix-rpi-deployment.sh" | sudo bash
```

This script automatically:
1. ✅ Removes conflicting `armguard.socket` unit
2. ✅ Detects your deployment location (`/opt/armguard` or `/home/ubuntu/ARMGUARD_RDS`)
3. ✅ Generates correct systemd service file with proper paths
4. ✅ Starts Gunicorn without socket activation conflicts
5. ✅ Verifies the service is running

## Full Deployment Process

```bash
# 1. Clone and run pre-check
cd ~
rm -rf ~/ARMGUARD_RDS
git clone https://github.com/Stealth3535/ARMGUARD_RDS.git
cd ARMGUARD_RDS
curl -sSL "https://raw.githubusercontent.com/Stealth3535/ARMGUARD_RDS/main/armguard/deployment/pre-deployment-check.sh" | bash

# 2. Run quick RPi setup
curl -sSL "https://raw.githubusercontent.com/Stealth3535/ARMGUARD_RDS/main/armguard/deployment/quick-rpi-setup.sh?$(date +%s)" | bash

# 3. Fix deployment paths and socket issues
curl -sSL "https://raw.githubusercontent.com/Stealth3535/ARMGUARD_RDS/main/armguard/deployment/fix-rpi-deployment.sh?$(date +%s)" | sudo bash

# 4. Verify deployment
sudo systemctl status armguard.service
ls -l /run/armguard.sock
curl http://localhost
```

## Verification Commands

```bash
# Check service status
sudo systemctl status armguard.service

# Check socket file
ls -l /run/armguard.sock

# View logs
sudo journalctl -u armguard.service -n 50

# Test web interface
curl http://localhost
curl http://$(hostname -I | awk '{print $1}')
```

## Manual Fix (If Needed)

If the automated script fails, run these commands manually:

```bash
# 1. Stop and remove socket unit
sudo systemctl stop armguard.socket armguard.service
sudo systemctl disable armguard.socket
sudo rm -f /etc/systemd/system/armguard.socket
sudo pkill gunicorn
sudo rm -f /run/armguard.sock

# 2. Edit service file
sudo nano /etc/systemd/system/armguard.service

# Update these lines:
# WorkingDirectory=/home/ubuntu/ARMGUARD_RDS/armguard  (or /opt/armguard/armguard)
# Environment="PATH=/home/ubuntu/ARMGUARD_RDS/venv/bin" (or /opt/armguard/venv/bin)
# ExecStart=/home/ubuntu/ARMGUARD_RDS/venv/bin/gunicorn ...  (or /opt/armguard/venv/bin/gunicorn)
# Remove any socket activation configuration

# 3. Reload and restart
sudo systemctl daemon-reload
sudo systemctl start armguard.service
sudo systemctl enable armguard.service
sudo systemctl status armguard.service
```

## Common Issues and Solutions

### Issue: "Can't connect to /run/armguard.sock"
**Cause:** Socket activation conflict (armguard.socket exists)  
**Solution:** Run the fix script or manually remove socket unit

### Issue: "No such file or directory" for venv
**Cause:** Wrong deployment path in service file  
**Solution:** Run the fix script to auto-detect correct path

### Issue: Service exits with status=1
**Cause:** Multiple issues (wrong path, socket conflict, missing deps)  
**Solution:** Run fix script, check logs with `sudo journalctl -xeu armguard.service`

## Support

If you continue to experience issues:
1. Run: `sudo journalctl -xeu armguard.service -n 100`
2. Check: `ls -la /home/ubuntu/ARMGUARD_RDS` or `ls -la /opt/armguard`
3. Verify venv: `ls -la /home/ubuntu/ARMGUARD_RDS/venv/bin/gunicorn`

---

**Last Updated:** February 5, 2026  
**Version:** 2.1.0-aplus
