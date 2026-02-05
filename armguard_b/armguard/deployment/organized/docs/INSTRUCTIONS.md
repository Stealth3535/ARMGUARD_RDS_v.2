# ArmGuard Deployment Instructions

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [VM Setup (Shared Folder)](#vm-setup-shared-folder)
3. [Development Deployment](#development-deployment)
4. [Production Deployment](#production-deployment)
5. [Post-Deployment Tasks](#post-deployment-tasks)
6. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### System Requirements
- **OS:** Ubuntu 20.04+ or Debian 11+
- **RAM:** Minimum 2GB (4GB recommended)
- **Disk:** Minimum 10GB free space
- **Python:** 3.10 or higher

### Required Packages
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv git nginx
```

---

## VM Setup (Shared Folder)

If using VMware with a shared folder from Windows host:

### 1. Install VMware Tools (if not already installed)
```bash
sudo apt install -y open-vm-tools open-vm-tools-desktop
```

### 2. Create Mount Point
```bash
sudo mkdir -p /mnt/hgfs
```

### 3. Mount Shared Folder
```bash
sudo vmhgfs-fuse .host:/Armguard /mnt/hgfs -o allow_other
```

### 4. Verify Mount
```bash
ls /mnt/hgfs/Armguard
# Should show: armguard/ serversetup/
```

### Auto-Mount on Boot (Optional)

To automatically mount the shared folder when the VM starts:

#### Step 1: Open fstab for editing
```bash
sudo nano /etc/fstab
```

#### Step 2: Add this line at the end of the file
```
.host:/Armguard /mnt/hgfs fuse.vmhgfs-fuse allow_other,defaults 0 0
```

#### Step 3: Save and exit
- Press `Ctrl + O` (write out)
- Press `Enter` (confirm filename)
- Press `Ctrl + X` (exit)

#### Step 4: Test the mount without rebooting
```bash
sudo mount -a
```

If no errors appear, verify it worked:
```bash
ls /mnt/hgfs/Armguard
```

#### Step 5: Reboot to confirm auto-mount
```bash
sudo reboot
```

After reboot, the shared folder should be automatically mounted at `/mnt/hgfs`.

**If you get errors:**
```bash
# Make sure the mount point exists
sudo mkdir -p /mnt/hgfs

# Ensure vmhgfs-fuse is installed
sudo apt install -y open-vm-tools open-vm-tools-desktop
```

---

## Development Deployment
---

## Hardening .env for Production

Before deploying to production, update your `.env` file as follows:

1. **Change DJANGO_ADMIN_URL to a random string**
	- Example: `DJANGO_ADMIN_URL=admin-x8k2m9p7`
	- Use any random string for extra security.

2. **Set all SSL/secure cookie settings to True**
	- Change:
	  ```
	  SECURE_SSL_REDIRECT=False
	  SESSION_COOKIE_SECURE=False
	  CSRF_COOKIE_SECURE=False
	  SECURE_HSTS_SECONDS=0
	  ```
	- To:
	  ```
	  SECURE_SSL_REDIRECT=True
	  SESSION_COOKIE_SECURE=True
	  CSRF_COOKIE_SECURE=True
	  SECURE_HSTS_SECONDS=31536000
	  ```

3. **Use PostgreSQL**
	- Change: `USE_POSTGRESQL=False` to `USE_POSTGRESQL=True`
	- Ensure your DB credentials (DB_NAME, DB_USER, DB_PASSWORD, etc.) are correct.

4. **Update allowed hosts and trusted origins**
	- Set your domain and server IP:
	  ```
	  DJANGO_ALLOWED_HOSTS=yourdomain.com,127.0.0.1,localhost,your-server-ip
	  CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
	  ```
	- Replace `yourdomain.com` and `your-server-ip` with your actual values.

After editing, save the file and restart your Django app for changes to take effect.

For testing and development purposes:

### Step 1: Mount Shared Folder
```bash
sudo vmhgfs-fuse .host:/Armguard /mnt/hgfs -o allow_other
```

### Step 2: Create Virtual Environment
```bash
python3 -m venv ~/armguard
source ~/armguard/bin/activate
```

### Step 3: Navigate to Project
```bash
cd /mnt/hgfs/Armguard/armguard
```

### Step 4: Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 5: Configure Environment
```bash
cp .env.example .env
nano .env  # Edit with your settings (see below)
```

**Key `.env` settings to review:**

- `DJANGO_SECRET_KEY`: Generate a new secret key for production (see .env comments)
- `DJANGO_DEBUG`: Set to `True` for development, `False` for production
- `DJANGO_ALLOWED_HOSTS`: Comma-separated list of allowed hosts (add your VM IP)
- `DJANGO_ADMIN_URL`: Change for security in production
- `USE_POSTGRESQL`: Set to `True` for PostgreSQL, `False` for SQLite
- `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`: Set to `True` for production/HTTPS
- Logging paths: Ensure `logs/` directory exists

See the provided `.env` template for full documentation and recommended values.
### Step 6: Initialize Database
```bash
python manage.py migrate
python manage.py createsuperuser
python assign_user_groups.py
```

### Step 7: Run Development Server
```bash
python manage.py runserver 0.0.0.0:8000
```

Access at: `http://your-vm-ip:8000`

---

## Production Deployment

For production use with Gunicorn + Nginx:

### Option A: Automated Deployment (Recommended)

#### Step 1: Copy Project to Server
```bash
# Mount shared folder first
sudo vmhgfs-fuse .host:/Armguard /mnt/hgfs -o allow_other

# Copy to server location
sudo mkdir -p /var/www/armguard
sudo cp -r /mnt/hgfs/Armguard/* /var/www/armguard/
cd /var/www/armguard
```

#### Step 2: Run Master Deployment
```bash
# For LAN-only deployment
sudo bash deployment/master-deploy.sh --network-type lan

# For WAN (internet-facing) deployment
sudo bash deployment/master-deploy.sh --network-type wan

# For hybrid (both LAN and WAN)
sudo bash deployment/master-deploy.sh --network-type hybrid
```

The script will guide you through:
- System package installation
- Python environment setup
- Database configuration
- SSL certificate generation
- Nginx configuration
- Firewall setup

---

### Option B: Manual Deployment

#### Step 1: Install System Dependencies
```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv nginx postgresql postgresql-contrib
```

#### Step 2: Create Project Directory
```bash
sudo mkdir -p /var/www/armguard
sudo cp -r /mnt/hgfs/Armguard/armguard/* /var/www/armguard/
sudo chown -R www-data:www-data /var/www/armguard
cd /var/www/armguard
```

#### Step 3: Create Virtual Environment
```bash
sudo -u www-data python3 -m venv .venv
sudo -u www-data .venv/bin/pip install --upgrade pip
sudo -u www-data .venv/bin/pip install -r requirements.txt
sudo -u www-data .venv/bin/pip install gunicorn
```

#### Step 4: Configure Environment
```bash
sudo cp .env.example .env
sudo nano .env
```

**Production `.env` settings:**
```
DEBUG=False
SECRET_KEY=generate-a-strong-random-key
ALLOWED_HOSTS=your-domain.com,your-server-ip
DATABASE_URL=sqlite:///db.sqlite3
```

#### Step 5: Initialize Application
```bash
sudo -u www-data .venv/bin/python manage.py migrate
sudo -u www-data .venv/bin/python manage.py collectstatic --noinput
sudo -u www-data .venv/bin/python manage.py createsuperuser
```

#### Step 6: Install Gunicorn Service
```bash
sudo bash deployment/install-gunicorn-service.sh
```

#### Step 7: Install Nginx
```bash
sudo bash deployment/install-nginx.sh your-domain.com
```

#### Step 8: Setup SSL (LAN)
```bash
sudo bash deployment/install-mkcert-ssl.sh armguard.rds.com
```

#### Step 9: Start Services
```bash
sudo systemctl enable gunicorn-armguard
sudo systemctl start gunicorn-armguard
sudo systemctl enable nginx
sudo systemctl restart nginx
```

---

### Using Both mkcert (LAN) and Let's Encrypt (WAN) SSL Certificates

If you want to enable both LAN (mkcert) and WAN/public (Let's Encrypt) SSL certificates for your deployment:

1. Complete the main deployment as usual, choosing either SSL option when prompted.
2. After deployment, run both SSL setup scripts manually for each domain:

   ```bash
   # For LAN/local SSL (mkcert)
	sudo bash deployment/install-mkcert-ssl.sh armguard.rds.com

   # For WAN/public SSL (Let's Encrypt)
   sudo bash deployment/install-letsencrypt-ssl.sh your-public-domain.com
   ```

3. Update your Nginx configuration to reference the correct certificate files for each domain/server block as needed.

> **Note:** The deployment script may only prompt for one SSL type. Running both scripts manually allows you to support both LAN and WAN access securely.

---

## Running the Pre-Deployment Check Directly

To manually run the pre-check script and validate your environment before deploying:

From the project root (where the armguard folder is located):
```bash
bash armguard/deployment/pre-check.sh
```

Or, if you are already inside the armguard directory:
```bash
bash deployment/pre-check.sh
```

> **Note:**
> - You must run the script as root to perform all checks:
>   ```bash
>   sudo bash deployment/pre-check.sh
>   ```
> - If you see errors like `$'\r': command not found`, convert the script to Unix (LF) line endings:
>   ```bash
>   sudo apt install -y dos2unix
>   sudo dos2unix armguard/deployment/pre-check.sh
>   ```

If the script reports `✓ Can reach PyPI via pip`, your Python and network setup are correct. If you see an error about PyPI, see the troubleshooting section above.

---

## Post-Deployment Tasks

### Verify Services
```bash
sudo systemctl status gunicorn-armguard
sudo systemctl status nginx
```

### Run Health Check
```bash
sudo bash deployment/health-check.sh
```

### Create Admin User (if not done)
```bash
cd /var/www/armguard
sudo -u www-data .venv/bin/python manage.py createsuperuser
```

### Setup User Groups
```bash
sudo -u www-data .venv/bin/python assign_user_groups.py
```

### View Logs
```bash
# Gunicorn logs
sudo journalctl -u gunicorn-armguard -f

# Nginx access logs
sudo tail -f /var/log/nginx/access.log

# Nginx error logs
sudo tail -f /var/log/nginx/error.log

# Application logs
sudo tail -f /var/log/armguard/app.log
```

---

## Quick Reference Commands

### Service Management
```bash
# Restart application
sudo systemctl restart gunicorn-armguard

# Restart Nginx
sudo systemctl restart nginx

# Stop application
sudo systemctl stop gunicorn-armguard

# Check status
sudo systemctl status gunicorn-armguard nginx
```

### Updates
```bash
cd /var/www/armguard
sudo bash deployment/update-armguard.sh
```

### Rollback
```bash
sudo bash deployment/rollback.sh
```

### Database Backup
```bash
cp /var/www/armguard/db.sqlite3 ~/backups/db-$(date +%Y%m%d).sqlite3
```

---

## Troubleshooting
### Script Errors: $'\r': command not found or syntax error
If you see errors like `$'\r': command not found` or `syntax error near unexpected token` when running deployment scripts from a shared folder, your `.sh` files likely have Windows (CRLF) line endings. Convert them to Unix (LF) line endings with:

```bash
sudo apt install -y dos2unix
sudo dos2unix /mnt/hgfs/Armguard/deployment/*.sh
sudo dos2unix /mnt/hgfs/Armguard/deployment/network_setup/*.sh
```
Then re-run your deployment command.

### Cannot Mount Shared Folder
```bash
# Check if vmhgfs-fuse is installed
sudo apt install -y open-vm-tools

# Verify shared folder exists in VMware settings
# VMware > VM > Settings > Options > Shared Folders

# Manual mount with debug
sudo vmhgfs-fuse -o allow_other -o debug .host:/Armguard /mnt/hgfs
```

### Port 8000 Already in Use
```bash
# Find process using port
sudo lsof -i :8000

# Kill process
sudo kill -9 <PID>
```

### Gunicorn Won't Start
```bash
# Check logs
sudo journalctl -u gunicorn-armguard -n 50

# Test manually
cd /var/www/armguard
sudo -u www-data .venv/bin/gunicorn core.wsgi:application --bind 0.0.0.0:8000
```

### Nginx 502 Bad Gateway
```bash
# Check if Gunicorn is running
sudo systemctl status gunicorn-armguard

# Check Gunicorn socket
ls -la /run/gunicorn-armguard.sock

# Check Nginx error logs
sudo tail -f /var/log/nginx/error.log
```

### Permission Denied Errors
```bash
# Fix ownership
sudo chown -R www-data:www-data /var/www/armguard

# Fix permissions
sudo chmod -R 755 /var/www/armguard
sudo chmod -R 775 /var/www/armguard/media
sudo chmod -R 775 /var/www/armguard/staticfiles
```

### Static Files Not Loading
```bash
cd /var/www/armguard
sudo -u www-data .venv/bin/python manage.py collectstatic --noinput
sudo systemctl restart nginx
```

---

## Access URLs

| Environment | URL |
|-------------|-----|
| Development | `http://your-vm-ip:8000` |
| Production (HTTP) | `http://your-domain/` |
| Production (HTTPS) | `https://your-domain/` |
| Admin Panel | `https://your-domain/admin/` |

---

## Support Files

| File | Purpose |
|------|---------|
| `master-deploy.sh` | Automated full deployment |
| `update-armguard.sh` | Safe updates with backup |
| `rollback.sh` | Restore from backup |
| `health-check.sh` | System health verification |
| `install-gunicorn-service.sh` | Gunicorn systemd service |
| `install-nginx.sh` | Basic Nginx setup |
| `install-mkcert-ssl.sh` | LAN SSL certificates |

---

## Pre-Deployment Validation: How to Fix All Errors and Warnings

If the pre-deployment validation script reports errors or warnings, use the following steps to resolve them:

### 1. ERROR: Cannot reach PyPI (Python package repository)

This is a network or firewall issue. You must resolve it or pip install will fail.

**Fix:**

- Check your VM’s internet connection:
	```bash
	ping pypi.org
	```
	If it fails, check your VM’s network settings (NAT/Bridged, etc.).

- Test HTTPS access to PyPI:
	```bash
	curl https://pypi.org
	```

	If you see HTML output, HTTPS is working. If you get an error, note the message (e.g., SSL, timeout, etc.).

	**If curl works but pip fails:**
	- Upgrade pip and setuptools (this fixes most SSL issues):
		```bash
		python3 -m pip install --upgrade pip setuptools
		```
	- Try installing a package to test pip:
		```bash
		pip install requests
		```
	- If this fails, note the error message for further troubleshooting. If you are behind a proxy, configure pip as shown below. If pip still fails after upgrading, check your Python SSL libraries or reinstall Python.

- Upgrade pip and setuptools (fixes some SSL issues):
	```bash
	python3 -m pip install --upgrade pip setuptools
	```

- Try installing a package to test pip:
	```bash
	pip install requests
	```
	If this fails, note the error message for further troubleshooting.

- If you are behind a proxy, configure pip:
	```bash
	pip config set global.proxy http://your-proxy:port
	```

	**How do you know if you are behind a proxy?**
	- You may be behind a proxy if you are on a corporate, university, or enterprise network, or if your internet access is filtered or restricted.
	- Signs include: browsers or other tools require proxy settings, or you see errors like "connection refused" or "403 Forbidden" when accessing external sites.
	- To check your proxy settings:
	  - On Linux, check environment variables:
	    ```bash
	    echo $http_proxy
	    echo $https_proxy
	    ```
	  - On Windows, check Internet Options > Connections > LAN Settings.
	  - Ask your network administrator or IT department for proxy details if unsure.

- If you have a firewall, allow outbound HTTPS (port 443) to pypi.org.

- If you have no internet, manually download required Python packages on another machine and transfer them to the VM.

**If curl and pip both fail:** Your firewall or proxy may be blocking HTTPS.

**If curl works but pip fails:** It’s likely a pip or Python SSL issue. Upgrading pip and setuptools usually resolves this.

### 2. WARNING: Port 80 already in use

Port 80 is used by nginx or another service.

**Fix:**
- If nginx is running from a previous install, you can stop it before deployment:
	```bash
	sudo systemctl stop nginx
	```
- Or, let the deployment script handle it (it may restart nginx as needed).
- If another service is using port 80, stop or reconfigure it:
	```bash
	sudo lsof -i :80
	sudo kill -9 <PID>
	```

### 3. WARNING: /var/www/armguard already exists

The deployment script will clean this up, but if you want to be sure:

**Fix:**
- Backup any important data from /var/www/armguard.
- Remove the directory manually:
	```bash
	sudo rm -rf /var/www/armguard
	```
- Or, let the deployment script handle it (it should prompt or clean up automatically).

---
**After fixing the PyPI error, re-run the pre-checks. The warnings do not block deployment, but the PyPI error does.**

---

## Quick Start Summary

```bash
# 1. Mount shared folder
sudo vmhgfs-fuse .host:/Armguard /mnt/hgfs -o allow_other

# 2. Copy and deploy
sudo cp -r /mnt/hgfs/Armguard/armguard /var/www/armguard
cd /var/www/armguard
sudo bash deployment/master-deploy.sh --network-type lan

# 3. Done! Access at https://your-vm-ip/
```
