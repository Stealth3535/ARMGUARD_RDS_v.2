# 🛡️ Secure Django Deployment on Ubuntu VM (LAN, VMware, Shared Folder)

This guide explains how to securely deploy your Django app on an Ubuntu Server VM (running in VMware Workstation), using a Windows host shared folder for code, and enabling HTTPS access over your LAN.

---

## 📦 Prerequisites
- Ubuntu Server VM running in VMware Workstation
- Windows host with project folder shared to VM (e.g., `/mnt/hgfs/Armguard`)
- Python, pip, and virtualenv set up in the VM
- Django app and dependencies installed in a venv (in VM)
- Root/sudo access on the VM

---

## 1️⃣ Prepare Your Project

1. **Ensure your code is accessible in the VM:**
   - Shared folder is mounted at `/mnt/hgfs/Armguard` (or similar)
2. **Create and activate a Python virtual environment in the VM:**
   ```bash
   cd ~
   python3 -m venv venv
   source ~/venv/bin/activate
   pip install -r /mnt/hgfs/Armguard/requirements.txt
   ```
3. **Copy and edit your `.env` file:**
   ```bash
   cp /mnt/hgfs/Armguard/.env.example /mnt/hgfs/Armguard/.env
   # Edit .env and set a strong DJANGO_SECRET_KEY and correct ALLOWED_HOSTS
   ```

---

## 2️⃣ Run Initial Migrations & Collect Static Files

```bash
cd /mnt/hgfs/Armguard
python manage.py migrate
python manage.py collectstatic --noinput
```

---

## 3️⃣ Move to Native Linux Directory (Recommended for Production)
For best performance and permissions, copy your project to `/var/www/armguard`:
```bash
sudo mkdir -p /var/www/armguard
sudo cp -r /mnt/hgfs/Armguard/* /var/www/armguard/
cd /var/www/armguard
```

---

## 4️⃣ Install and Configure Gunicorn

1. **Install Gunicorn:**
   ```bash
   pip install gunicorn
   ```
2. **Test Gunicorn:**
   ```bash
   gunicorn --bind unix:/var/www/armguard/gunicorn.sock core.wsgi:application
   ```
3. **Set up Gunicorn as a service:**
   - Edit and use `deployment/gunicorn-armguard.service` as described in the deployment folder.
   - Enable and start the service:
     ```bash
     sudo cp deployment/gunicorn-armguard.service /etc/systemd/system/gunicorn.service
     sudo systemctl daemon-reload
     sudo systemctl enable gunicorn
     sudo systemctl start gunicorn
     sudo systemctl status gunicorn
     ```

---

## 5️⃣ Install and Configure Nginx

1. **Run the installer script:**
   ```bash
   sudo bash deployment/install-nginx.sh
   ```
2. **Check Nginx status:**
   ```bash
   sudo systemctl status nginx
   sudo nginx -t
   ```
3. **Default access:**
   - `http://<your-vm-ip>`

---

## 6️⃣ Enable HTTPS with mkcert (LAN/Development SSL)

1. **Run the mkcert SSL installer:**
   ```bash
   sudo bash deployment/install-mkcert-ssl.sh
   ```
2. **Import the mkcert CA certificate on your Windows host:**
   - Find the CA root: `mkcert -CAROOT`
   - Copy `rootCA.pem` to your Windows machine and import it into Trusted Root Certification Authorities.
3. **Update your `.env` for SSL:**
   ```env
   SECURE_SSL_REDIRECT=True
   SESSION_COOKIE_SECURE=True
   CSRF_COOKIE_SECURE=True
   SECURE_HSTS_SECONDS=31536000
   ```
4. **Restart Gunicorn and Nginx:**
   ```bash
   sudo systemctl restart gunicorn
   sudo systemctl restart nginx
   ```
5. **Access your app securely:**
   - `https://<your-vm-ip>/`

---

## 7️⃣ Troubleshooting
- Check logs: `/var/log/nginx/armguard_error.log`, `/var/log/nginx/armguard_access.log`, `sudo journalctl -u gunicorn`
- Test Nginx config: `sudo nginx -t`
- Check Gunicorn socket: `ls -la /var/www/armguard/gunicorn.sock`
- Firewall: Allow ports 80 and 443 (`sudo ufw allow 80`, `sudo ufw allow 443`)

---

## 8️⃣ Notes
- For development, you can keep using the shared folder, but for production, always deploy from a native Linux directory.
- For public deployment, use Let's Encrypt as described in `NGINX_SSL_GUIDE.md`.

---

**You now have a secure, production-like Django deployment on your Ubuntu VM, accessible over HTTPS from your LAN!**
