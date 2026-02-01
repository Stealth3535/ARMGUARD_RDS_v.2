# 🌐 Complete LAN/WAN Deployment Guide: ArmGuard Military Inventory

**Enterprise Military Application Deployment** - LAN/WAN Hybrid Architecture

## 📋 Overview

This guide covers deploying ArmGuard as a **LAN/WAN hybrid military inventory system** with **security-first architecture**:

**🔒 LAN Operations (High Security):**
- ✅ **Registration & Transactions** (LAN only via Raspberry Pi server)
- ✅ **Inventory Management** (Add/Edit/Delete items)
- ✅ **User Registration** (Personnel enrollment) 
- ✅ **Critical Operations** (Sensitive military data)

**🌐 WAN Operations (Read-Only Status):**
- ✅ **Status Checking** (Personnel check their transaction history)
- ✅ **Reports & Analytics** (Authorized personnel only)
- ✅ **Read-Only Access** (No sensitive operations)
- ✅ **Authorization-Based** (Role-based permissions)

**Network Architecture:**
```
Developer PC ←→ Router (LAN) ←→ Raspberry Pi Server ←→ Armory PC
                    ↓
               Internet (WAN)
                    ↓  
              Status Checking Only
```

**Security Model:** **Write via LAN, Read via WAN**

---

## �️ Phase 1: Choose Network Architecture (10 minutes)

### Option A: LAN-Only Deployment (Recommended for Secure Environments)
**Best for: Military bases, secure facilities, internal operations**
- ✅ **No internet required** after initial setup
- ✅ **Maximum security** - isolated network
- ✅ **Local SSL certificates** with mkcert
- ✅ **Internal domain names** (.local, .mil, .internal)
- ✅ **No monthly costs** after hardware

**Example Setup:**
- Server: `armguard.base.mil` or `armguard.local`
- Access: Only from internal network
- SSL: Self-signed or internal CA
- Users: Military personnel on base network

### Option B: WAN-Accessible (Internet Deployment)
**Best for: Multi-location operations, remote access**
- ✅ **Internet access** from anywhere
- ✅ **Public SSL certificates** (Let's Encrypt)
- ✅ **Domain name required**
- ✅ **Remote user access**
- ⚠️ **Requires security hardening**

**Example Setup:**
- Server: `armguard.yourbase.mil` or `inventory.company.com`
- Access: Internet + VPN for security
- SSL: Public certificates
- Users: Authorized personnel with credentials

### Option C: Military Hybrid LAN/WAN (Your Architecture)
**Perfect for: Military operations with security-first approach**
- ✅ **LAN**: Registration, transactions, inventory management (Raspberry Pi)
- ✅ **WAN**: Read-only status checking (authorized personnel)
- ✅ **Security separation**: Critical ops on LAN, status on WAN
- ✅ **Role-based access**: Different permissions per network
- ✅ **Hardware efficient**: Raspberry Pi can handle both

**Your Specific Setup:**
```
LAN Network (192.168.1.0/24):
├── Raspberry Pi Server (192.168.1.100)
├── Developer PC (192.168.1.10)  
├── Armory PC (192.168.1.20)
└── Router → Internet (WAN access for status only)
```

**Access Patterns:**
- **Armory PerRaspberry Pi LAN/WAN Server (Your Setup)
**Perfect for military armory operations:**

| Hardware | Specs | Cost | Purpose |
|----------|-------|------|---------|
| **Raspberry Pi 4** | 8GB RAM, 256GB SD | $100-150 | Main server (LAN + WAN) |
| **Network Switch** | 8-port gigabit | $30-50 | LAN connectivity |
| **UPS Battery** | 1000VA | $100-150 | Power backup |
| **External Storage** | 1TB USB SSD | $80-120 | Database backup |

**Raspberry Pi Server Setup:**
1. **Install Ubuntu Server 22.04** on Raspberry Pi
2. **Configure static IP**: `192.168.1.100`
3. **Set hostname**: `armguard-server.local`
4. **Enable SSH**: For remote administration
5. **Install Docker** (optional): For containerized deployment

**Network Configuration:**
```bash
# Set static IP on Raspberry Pi
sudo nano /etc/netplan/99-custom.yaml

network:
  version: 2
  ethernets:
    eth0:
      addresses:
        - 192.168.1.100/24
      gateway4: 192.168.1.1
      nameservers:
        addresses: [8.8.8.8, 1.1.1.1]
``` $400-800 | Small unit/outpost |
| **Raspberry Pi 4** | 8GB RAM, 256GB SD | $100-150 | Field operations |
| **VM on existing server** | Allocated resources | $0 | Existing infrastructure |

**LAN Server Setup Steps:**
1. **Install Ubuntu 22.04** on your hardware
2. **Configure static IP** (e.g., `192.168.1.100`)
3. **Set hostname** (e.g., `armguard-server.local`)
4. **Configure local DNS** or use IP address

### Option B: Cloud/VPS (WAN Accessible)
**For internet-accessible deployments:**

| Provider | Price | Specs | Security Features |
|----------|-------|-------|------------------|
| **AWS EC2** | $20-50/month | 2-4GB RAM | Military compliance available |
| **DigitalOcean** | $12-24/month | 2-4GB RAM | Good security features |
| **Linode** | $10-20/month | 2-4GB RAM | DDoS protection |
| **Government Cloud** | Varies | Varies | FedRAMP compliance |

### Option C: Hybrid Infrastructure
**Best of both worlds:**
- **Primary**: On-premise LAN server
- **Secondary**: Cloud backup/remote access
- **Network**: VPN tunnel between both
- **Access**: LAN for daily use, WAN for remote

### Network Architecture Examples

#### LAN-Only Architecture:
```
Military Network (192.168.1.0/24)
├── ArmGuard Server (192.168.1.100:443)
├── User Workstations (192.168.1.10-50)
├── Mobile Devices (WiFi access)
└── Printers/Scanners (192.168.1.200+)
```

#### WAN-Accessible Architecture:
```
Internet
├── Firewall/VPN Gateway
├── ArmGuard Server (Public IP:443)
├── Load Balancer (optional)
└── Database (private subnet)
```

#### Hybrid Architecture:
```
LAN: armguard.base.local:8443 (mkcert SSL)
WAN: secure.yourbase.mil:443 (Let's Encrypt SSL)
├── Internal users → LAN endpoint
├── Remote users → WAN endpoint (VPN required)
└── Both endpoints → Same database
```

---

## 🔗 Phase 3: DNS Configuration (20 minutes + propagation time)

### Step 1: Point Domain to Server

**At your domain registrar:**

1. **Find DNS Management**
   - Log into your domain registrar
   - Find "DNS Management" or "Nameservers"

2. **Add A Records**
   ```
   Type: A
   Name: @ (or blank)
   Value: 123.456.789.123 (your server IP)
   TTL: 3600

   Type: A  
   Name: www
   Value: 123.456.789.123 (your server IP)
   TTL: 3600
   ```

3. **Add CNAME (Optional)**
   ```
   Type: CNAME
   Name: admin
   Value: yourdomain.com
   ```

### Step 2: Verify DNS Propagation
```bash
# Check if DNS is working (run from your local machine)
nslookup yourdomain.com
dig yourdomain.com

# Should return your server IP
```

**DNS Propagation Time:** 15 minutes to 48 hours (usually 2-6 hours)

---

## 🚀 Phase 4: Server Preparation (30 minutes)

### Step 1: Connect to Server
```bash
# SSH into your server
ssh root@yourdomain.com
# or
ssh root@123.456.789.123
```

### Step 2: Initial Server Setup
```bash
# Update system
apt update && apt upgrade -y

# Create non-root user
adduser armguard
usermod -aG sudo armguard

# Switch to new user
su - armguard
```

### Step 3: Upload Your Code
**Option A: Git Clone (Recommended)**
```bash
# Install git
sudo apt install git -y

# Clone your repository
git clone https://github.com/yourusername/armguard.git
# or upload via SCP if using local files
```

**Option B: SCP Upload**
```bash
# From your local machine
scp -r /path/to/armguard/ armguard@yourdomain.com:/home/armguard/
```

---

## 🛠️ Phase 5: ArmGuard LAN/WAN Deployment (45-90 minutes)

### Step 1: Choose Your Network Architecture
```bash
cd armguard/deployment

# Check your network setup options
ls network_setup/
# Shows: nginx-lan.conf, nginx-wan.conf, setup-lan-network.sh, etc.
```

### Step 2: Configure Network Type

#### Option A: LAN-Only Deployment (Military/Secure)
```bash
cd methods/production
sudo nano config.sh

# LAN Configuration:
export NETWORK_Military Hybrid (Your Architecture)
```bash
# Hybrid Configuration for security-separated operations:
export NETWORK_TYPE="hybrid"
export DOMAIN_LAN="armguard.local"          # LAN access
export DOMAIN_WAN="status.yourbase.mil"     # WAN status checking
export SSL_EMAIL="admin@yourbase.mil"
export LAN_PORT="8443"                      # Full access (transactions)
export WAN_PORT="443"                       # Read-only access (status)

# Security separation settings:
export LAN_PERMISSIONS="full"               # All operations on LAN
export WAN_PERMISSIONS="readonly"           # Status checking only on WAN
export ENABLE_OPERATION_FILTERING="true"    # Filter operations by network
```

### Step 3: Deploy to Raspberry Pi with Security Separation

#### Your Military Hybrid Deployment:
```bash
# SSH to your Raspberry Pi
ssh pi@192.168.1.100
# or
ssh armguard@armguard-server.local

# Navigate to deployment
cd armguard/deployment

# Deploy with military hybrid configuration
./deploy-master.sh production --network-type hybrid

# This configures:
# - LAN (8443): Full access for armory operations
# - WAN (443): Status checking for remote personnel
```

### Step 4: Configure Security-Based Access Control

#### Set Up Role-Based Permissions:
```bash
cd /opt/armguard/armguard
source ../venv/bin/activate

# Create user groups via Django admin or management command
python manage.py shell << 'EOF'
from django.contrib.auth.models import Group, Permission

# Create security-based groups
armory_group, _ = Group.objects.get_or_create(name='ArmoryPersonnel')
remote_group, _ = Group.objects.get_or_create(name='RemotePersonnel')
admin_group, _ = Group.objects.get_or_create(name='SystemAdmins')

# Armory Personnel (LAN): Full access
armory_permissions = Permission.objects.filter(
    codename__in=['add_', 'change_', 'delete_', 'view_']
)
armory_group.permissions.set(armory_permissions)

# Remote Personnel (WAN): View-only access
remote_permissions = Permission.objects.filter(
    codename__startswith='view_'
)
remote_group.permissions.set(remote_permissions)
EOF
```

### Step 5: Network Access Configuration

#### LAN Access (Raspberry Pi - Full Operations):
- **URL**: `https://armguard.local:8443` or `https://192.168.1.100:8443`
- **Users**: Armory personnel on base network
- **Operations**: Registration, transactions, inventory management
- **Security**: Network isolation + local SSL

#### WAN Access (Internet - Status Only):
- **URL**: `https://status.yourbase.mil` 
- **Users**: Remote personnel with credentials
- **Operations**: Status checking, reports, read-only access
- **Security**: Public SSL + VPN recommendednsure domain points to server first!
nslookup yourdomain.com

# Deploy to WAN
./deploy-master.sh production --network-type wan

# Access: https://yourdomain.com
```

#### Hybrid Deployment:
```bash
# Deploy hybrid (both LAN and WAN)
./deploy-master.sh production --network-type hybrid

# Access:
# LAN: https://armguard.local:8443
# WAN: https://yourdomain.com:443
```

### Step 4: Create Admin User
```bash
cd /opt/armguard/armguard
source ../venv/bin/activate
python manage.py createsuperuser
```

---

## 🔒 Phase 6: SSL Certificate Setup (15 minutes)

### Automatic SSL (Let's Encrypt)
If the deployment script succeeded:
```bash
# SSL should be automatic, verify with:
sudo certbot certificates

# Test renewal
sudo certbot renew --dry-run
```

### Manual SSL Setup (if needed)
```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx -y

# Get SSL certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Test automatic renewal
sudo certbot renew --dry-run
```

---

## 🧪 Phase 7: Testing & Verification (15 minutes)

### Step 1: Basic Connectivity
```bash
# Test HTTP redirect to HTTPS
curl -I http://yourdomain.com

# Test HTTPS
curl -I https://yourdomain.com
```

### Step 2: Application Testing
1. **Visit your site**: https://yourdomain.com
2. **Admin access**: https://yourdomain.com/admin  
3. **Check functionality**: Create test inventory items
4. **Mobile test**: Check responsive design

### Step 3: Health Check
```bash
cd /opt/armguard/armguard/deployment/methods/production
./health-check.sh
```

---

## 🐛 Troubleshooting Common Issues

### Issue 1: Domain Not Resolving
```bash
# Check DNS propagation
nslookup yourdomain.com
dig yourdomain.com

# Wait longer if recent DNS changes
# DNS can take up to 48 hours
```

### Issue 2: SSL Certificate Failed
```bash
# Check if domain points to server
dig yourdomain.com

# Try manual SSL setup
sudo certbot --nginx -d yourdomain.com --dry-run

# Check nginx configuration
sudo nginx -t
```

### Issue 3: Application Not Loading
```bash
# Check services
sudo systemctl status armguard
sudo systemctl status nginx
sudo systemctl status postgresql

# Check logs
sudo journalctl -u armguard -f
sudo tail -f /var/log/nginx/error.log
```

### Issue 4: 502 Bad Gateway
```bash
# Usually means Gunicorn is down
sudo systemctl restart armguard
sudo systemctl status armguard

# Check Gunicorn process
ps aux | grep gunicorn
```

### Issue 5: Database Connection Error
```bash
# Check PostgreSQL
sudo systemctl status postgresql
sudo -u postgres psql -l

# Check database configuration
cd /opt/armguard/armguard
grep DATABASE .env
```

---

## 📊 Cost Breakdown

### Monthly Costs:
- **Domain**: $1-2/month (paid annually)
- **VPS Hosting**: $5-10/month  
- **SSL Certificate**: Free (Let's Encrypt)
- **Backups**: $2-5/month (optional)

**Total: $8-17/month**

### One-time Setup:
- **Domain Registration**: $10-15/year
- **Setup Time**: 2-4 hours of your time

---

## 🎯 Quick Start Checklist

### Before You Begin:
- [ ] Choose and register domain name
- [ ] Select hosting provider and create server
- [ ] Have your ArmGuard code ready
- [ ] Email address for SSL certificates

### Deployment Steps:
- [ ] Configure DNS A records
- [ ] SSH into server and create user
- [ ] Upload/clone ArmGuard code
- [ ] Update config.sh with your domain
- [ ] Run `./deploy-master.sh production`
- [ ] Create admin user
- [ ] Test HTTPS access
- [ ] Verify all functionality

### Post-Deployment:
- [ ] Set up regular backups
- [ ] Configure monitoring alerts
- [ ] Test disaster recovery
- [ ] Document admin procedures

---

## 🆘 Need Help?

### Quick Fixes:
```bash
# Restart everything
sudo systemctl restart nginx postgresql armguard

# Check system status
./deploy-master.sh status

# View deployment logs
sudo journalctl -u armguard -n 50
```

### Get Support:
1. **Check logs first**: `/var/log/armguard/` and `journalctl`
2. **Test DNS**: Use online DNS checker tools  
3. **SSL issues**: Check with SSL checker tools
4. **Community forums**: DigitalOcean, Stack Overflow
5. **Provider docs**: Most hosting providers have excellent documentation

---

## 🚀 Success! Your App is Live

Once complete, you'll have:
- ✅ **Live application** at https://yourdomain.com
- ✅ **Admin interface** at https://yourdomain.com/admin
- ✅ **SSL certificate** (HTTPS security)
- ✅ **Automatic backups** configured
- ✅ **Production monitoring** set up
- ✅ **Professional deployment** ready for users

**Your ArmGuard application is now live and accessible to users worldwide!** 🎉