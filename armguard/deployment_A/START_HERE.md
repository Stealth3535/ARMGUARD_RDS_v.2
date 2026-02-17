# 🚀 ArmGuard Deployment - START HERE

## 🚀 One Command Deployment

```bash
cd ~/ARMGUARD_RDS_v.2/armguard/deployment_A
sudo bash ubuntu-deploy.sh --production
```

**That's it!** This is the canonical production path.

---

## Manual Deployment Paths

### 🎯 Production (Direct)
```bash
cd ~/ARMGUARD_RDS_v.2/armguard/deployment_A/methods/production
sudo bash deploy-armguard.sh
```

Use this only for advanced troubleshooting when the wrapper path cannot be used.

### 🐳 Docker (Direct)
```bash
cd ~/ARMGUARD_RDS_v.2/armguard/deployment_A/methods/docker-testing
docker-compose up -d
```

### 🔧 Development (Direct)
```bash
cd ~/ARMGUARD_RDS_v.2/armguard
python manage.py runserver 0.0.0.0:8000
```

---

## 📁 Folder Structure Explained

```
deployment_A/
├── START_HERE.md           ← You are here
├── methods/
│   ├── production/         ← Main deployment (USE THIS)
│   │   └── deploy-armguard.sh
│   ├── docker-testing/     ← Docker containers
│   ├── basic-setup/        ← Manual VM setup
│   └── vmware-setup/       ← VMware-specific
├── legacy_archive/         ← Old scripts (IGNORE)
└── docs_archive/           ← Old documentation (IGNORE)
```

**Ignore Everything Else** - Those are old scripts, archives, or specialized tools.

---

## 🆘 Troubleshooting

### Already Started Deployment?

If you have a failed deployment, clean up first:

```bash
cd ~/ARMGUARD_RDS_v.2/armguard
git pull origin main
sudo bash deployment_A/methods/production/cleanup-and-redeploy.sh
```

### Permission Issues?

```bash
cd ~/ARMGUARD_RDS_v.2
sudo chown -R $USER:$USER .
git pull origin main
```

### Want to Start Fresh?

```bash
# Remove database and start over
sudo systemctl stop gunicorn-armguard
sudo -u postgres dropdb armguard_db
sudo bash deployment_A/methods/production/deploy-armguard.sh
```

---

## ⚙️ What Gets Installed

**Services:**
- Gunicorn (WSGI server)
- Nginx (Web server + reverse proxy)
- PostgreSQL or SQLite (Database)
- Redis (WebSocket support)
- Daphne (ASGI for WebSockets)

**Network:**
- Hybrid LAN + WAN support
- SSL certificates (mkcert or Let's Encrypt)
- Firewall configuration
- Static files serving

**Security:**
- Secure admin URL
- Network-based access control
- Device authorization
- Personnel tracking

---

## 📋 Pre-Deployment Checklist

- [ ] Fresh Ubuntu/Raspberry Pi OS installation
- [ ] Internet connection active
- [ ] User has sudo privileges
- [ ] Git repository cloned to `~/ARMGUARD_RDS_v.2`
- [ ] Latest code: `git pull origin main`

---

## 🎯 The One Command You Need

```bash
cd ~/ARMGUARD_RDS_v.2/armguard/deployment_A && git pull origin main && sudo bash ubuntu-deploy.sh --production
```

This will:
1. Navigate to project
2. Get latest code
3. Run deployment

**Done!** 🎉

---

## 📞 Need Help?

**Check logs:**
```bash
sudo journalctl -u gunicorn-armguard -n 100
```

**Service status:**
```bash
sudo systemctl status gunicorn-armguard
sudo systemctl status nginx
```

**Database access:**
```bash
sudo -u postgres psql armguard_db
```

---

## 🚫 What NOT to Use

❌ `01_setup.sh` - Old modular approach  
❌ `deploy.sh` - Legacy multi-menu path  
❌ `deploy-master.sh` - Deprecated  
❌ `systematized-deploy.sh` - Old version  
❌ Scripts in `legacy_archive/` - Archived  
❌ Multiple validator scripts - Built into deploy-armguard.sh  

**Use ONLY:** `ubuntu-deploy.sh --production`

---

**Status:** ✅ Simplified deployment system  
**Last Updated:** February 11, 2026  
**Tested On:** Ubuntu 24.04, Raspberry Pi OS
