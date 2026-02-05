# 🚀 ArmGuard Raspberry Pi 4B + VPN Integration - Complete Deployment Guide

## 📋 Military Inventory Management System with Secure Remote Access

This guide provides complete deployment of your ArmGuard military inventory management system on Raspberry Pi 4B with VPN integration for secure remote access.

**✅ Status**: Production-ready deployment with PostgreSQL, VPN integration, and enterprise security.

---

## 🛠️ Prerequisites

### Hardware Requirements
- **Raspberry Pi 4B** (4GB RAM recommended, 2GB minimum)
- **MicroSD Card** (32GB minimum, 64GB recommended)
- **Network Connection** (Ethernet preferred for stability)
- **Power Supply** (Official RPi 4B adapter)

### Software Requirements
- **Ubuntu Server 22.04** or **Raspberry Pi OS** (64-bit recommended)
- **SSH access** enabled
- **Internet connection** for initial setup
- **Router with port forwarding** capability (for external VPN access)

### Network Setup
- **Local Network**: Your existing network (e.g., 192.168.0.x)
- **VPN Network**: 10.0.0.0/24 (created automatically)
- **Port Forwarding**: UDP port 51820 → Your RPi IP (for external VPN)

---

## 🚀 Complete One-Command Deployment

### Step 1: Prepare Your Raspberry Pi

1. **Flash and boot your RPi with Ubuntu Server 22.04**
2. **Enable SSH and connect to network**
3. **Update the system:**
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

### Step 2: Clone ArmGuard Project

```bash
# Clone to /home/armguard/armguard (or use your existing location)
cd /home/armguard
git clone https://your-repo-url/armguard.git
cd armguard
```

### Step 3: Run Complete Deployment

```bash
# Navigate to deployment directory
cd /home/armguard/armguard/deployment

# Make scripts executable
chmod +x *.sh

# Run complete deployment
sudo ./rpi4b-vpn-deploy.sh
```

### Step 4: Handle Any Issues (if needed)

If you encounter dependency conflicts:
```bash
sudo ./fix-dependencies.sh
```

If you need to fix database configuration:
```bash
sudo ./setup-postgresql.sh
```

If services aren't running:
```bash
sudo ./setup-gunicorn-service.sh
```

### Step 5: Finalize Deployment

```bash
# Run final deployment completion
sudo ./finalize-deployment.sh
```

**Deployment Complete!** The system will provide your access URLs and status.

**That's it!** The script will automatically:
- ✅ Install all system dependencies (Python, Nginx, PostgreSQL, WireGuard)
- ✅ Set up the Django application with proper permissions
- ✅ Configure the database and create migrations
- ✅ Set up Gunicorn as a system service
- ✅ Configure Nginx reverse proxy
- ✅ Install and configure WireGuard VPN server
- ✅ Set up firewall and security measures
- ✅ Create all necessary directories and permissions

**Note:** If you encounter package dependency conflicts, the script includes a `fix-dependencies.sh` helper to resolve common Ubuntu package conflicts automatically.

---

## home/armguard/armguard/deployment

# Make  create VPN clients for secure remote access:

### Generate Client Configurations

```bash
# Navigate to the deployment directory
cd /opt/armguard/deployment

# Mahome/armguardclient generator executable
chmod +x rpi4b-generate-client.sh

# Generate clients for different roles
sudo ./rpi4b-generate-client.sh john-smith commander
sudo ./rpi4b-generate-client.sh jane-doe armorer
sudo ./rpi4b-generate-client.sh emergency-user emergency
sudo ./rpi4b-generate-client.sh regular-user personnel
```

### Access Control by Role

| Role | Permissions | Network Access |
|------|-------------|----------------|
| **Commander** | Full system access, all reports | Full VPN + LAN |
| **Armorer** | Equipment inventory, maintenance | Limited VPN + LAN |
| **Emergency** | Critical equipment only | Restricted VPN |
| **Personnel** | Personal status checking | Minimal VPN |

### Client Installation

**Desktop (Windows/Mac/Linux):**
1. Install WireGuard client
2. Import the `.conf` file from `/etc/wireguard/clients/`
3. Connect and visit `http://10.0.0.1`

**Mobile (iOS/Android):**
1. Install WireGuard app
2. Scan the QR code from `/etc/wireguard/clients/*.png`
3. Connect and browse to `http://10.0.0.1`

---

## 🌐 Access Your ArmGuard System

### Local Network Access (LAN)
- **Main Interface**: `http://YOUR_RPI_IP`
- **Admin Panel**: `http://YOUR_RPI_IP/admin`
- **Full functionality**: ✅ Transactions, inventory, user management

### VPN Remote Access
- **Main Interface**: `http://10.0.0.1` (via VPN)
- **Admin Panel**: `http://10.0.0.1/admin` (via VPN)
- **Functionality**: Read-only status, reports (transactions require LAN)

---

## 🛡️ Security Features

### Network Security
- ✅ **Transactions LAN-Only**: All armory transactions require physical LAN access
- ✅ **VPN Read-Only**: Remote users can view inventory status only
- ✅ **Firewall Protection**: UFW configured with minimal open ports
- ✅ **Role-Based Access**: Different VPN clients have different permissions

### Encryption & Authentication
- ✅ **WireGuard VPN**: ChaCha20Poly1305 encryption
- ✅ **Django Security**: CSRF protection, secure headers
- ✅ **SSH Hardening**: Key-based authentication recommended
- ✅ **Database Security**: Local SQLite with proper permissions

---

## 📊 System Management

### Check System Status
```bash
# Check all services
sudo systemctl status armguard nginx wg-quick@wg0

# View logs
sudo tail -f /var/log/armguard/deployment.log

# Check VPN connections
sudo wg show
```

### Backup and Maintenance
```bash
# Backup database
cp /opt/armguard/db.sqlite3 /opt/armguard/backups/db-$(date +%Y%m%d).sqlite3

# Update ArmGuard code
cd /opt/armguard
git pull  # if using git
sudo systemctl restart armguard

# VPN maintenance
sudo systemctl restart wg-quick@wg0
```

---

## 🔧 Router Configuration (For External VPN Access)

To allow VPN connections from outside your local network:

1. **Find your RPi's local IP**: `hostname -I`
2. **Log into your router's admin panel**
3. **Set up port forwarding**:
   - External Port: `51820`
   - Internal Port: `51820`
   - Protocol: `UDP`
   - Internal IP: Your RPi's IP
4. **Test from external network**

---

## 🚨 Troubleshooting

### Common Issues

**Package dependency conflicts during installation:**
```bash
# Use the fix script to resolve conflicts
cd /home/armguard/armguard/deployment
sudo ./fix-dependencies.sh
```

**Service won't start:**
```bash
# Check service status
sudo systemctl status armguard
sudo journalctl -u armguard -f

# Restart services
sudo systemctl restart armguard nginx
```

**VPN connection issues:**
```bash
# Check VPN status
sudo wg show
sudo systemctl status wg-quick@wg0

# Restart VPN
sudo systemctl restart wg-quick@wg0
```

**Permission issues:**
```bash
# Fix file permissions
sudo chown -R www-data:www-data /opt/armguard
sudo chown -R www-data:www-data /var/www/armguard
```

### Getting Help

- **Logs location**: `/var/log/armguard/`
- **Configuration**: `/opt/armguard/.env`
- **VPN configs**: `/etc/wireguard/`
- **Web files**: `/var/www/armguard/`

---

## 🎉 Deployment Complete! 

Your ArmGuard Military Inventory System is now fully deployed and operational.

### 🌐 Access Your System

**Your system is accessible at:**
- **Main Application**: `http://192.168.0.177` (your RPi IP)
- **Admin Panel**: `http://192.168.0.177/admin`
- **Mobile Access**: `http://192.168.0.177` (from any device on your network)

**After VPN setup:**
- **VPN Remote Access**: `http://10.0.0.1` (through VPN tunnel)

### 🔐 Security Features Active

- ✅ **Transactions LAN-Only**: All armory transactions require physical network access
- ✅ **VPN Read-Only**: Remote users can view inventory status only  
- ✅ **PostgreSQL Database**: Enterprise-grade data storage
- ✅ **Role-Based VPN Access**: 4 security levels (Commander, Armorer, Emergency, Personnel)
- ✅ **Firewall Protection**: UFW configured with minimal ports open
- ✅ **Service Auto-Start**: All services start automatically on boot

### 📚 Documentation

- **[Operations Manual](OPERATIONS_MANUAL.md)** - Daily operations & maintenance
- **[Deployment Summary](../DEPLOYMENT_SUMMARY.txt)** - Complete system information
- **VPN Client Generation**: Use `rpi4b-generate-client.sh`

### 🚀 Next Steps

1. **Create Admin Account**: 
   ```bash
   cd /opt/armguard && source venv/bin/activate && python manage.py createsuperuser
   ```

2. **Generate VPN Clients**:
   ```bash
   cd /home/armguard/armguard/deployment
   sudo ./rpi4b-generate-client.sh username role
   ```

3. **Test All Access Methods**:
   - Local: `http://192.168.0.177`
   - Admin: `http://192.168.0.177/admin`
   - Mobile: Browse to your Pi's IP from phone/tablet

4. **Set Up Regular Backups** (see Operations Manual)

### 🛠️ Finalization Command

Run the final deployment check:
```bash
cd /home/armguard/armguard/deployment
chmod +x finalize-deployment.sh
sudo ./finalize-deployment.sh
```

This will verify all services, create a deployment summary, and provide your final system status.

---

**🎯 Your ArmGuard system is ready for production use!**

*Guide completed: February 3, 2026*