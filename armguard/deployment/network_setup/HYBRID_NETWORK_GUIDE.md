# 🔐 ArmGuard Hybrid Network Setup - Complete Guide

## Overview

This guide explains how to set up a **secure hybrid network** where:
- **LAN network**: Isolated subnet for secure armory operations (mkcert SSL)
- **WAN network**: Public personnel login portal (ZeroSSL/Let's Encrypt)
- Complete network isolation with proper firewall rules

---

## 📐 Architecture Explained

### Why Hybrid Network?

1. **Security Isolation**: Armory operations (sensitive inventory data) are completely isolated from public internet
2. **Role Separation**: Armory PC has full access, personnel have limited portal access
3. **Attack Surface Reduction**: Admin panel and inventory management never exposed to internet
4. **Certificate Flexibility**: Self-signed for LAN (no public CA needed), public CA for WAN

---

## 🔐 How mkcert and ZeroSSL Coexist

### The Magic: Different Domains/IPs

Both certificate systems work together because they serve **completely different endpoints**:

| Aspect | LAN (mkcert) | WAN (ZeroSSL) |
|--------|--------------|----------------|
| **Domain/IP** | 192.168.10.1:8443 | login.yourdomain.com:443 |
| **Nginx Server Block** | Separate | Separate |
| **Certificate Storage** | /etc/ssl/armguard/lan/ | /etc/letsencrypt/live/domain/ |
| **Trust Model** | Manual CA install | Public CA (trusted) |
| **Access** | LAN only | Internet |

### Certificate Non-Conflict

```nginx
# LAN Server Block (mkcert)
server {
    listen 192.168.10.1:8443 ssl;
    ssl_certificate /etc/ssl/armguard/lan/armguard-lan-cert.pem;
    ssl_certificate_key /etc/ssl/armguard/lan/armguard-lan-key.pem;
    server_name 192.168.10.1;
}

# WAN Server Block (ZeroSSL)
server {
    listen 443 ssl;  # All interfaces
    ssl_certificate /etc/letsencrypt/live/login.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/login.yourdomain.com/privkey.pem;
    server_name login.yourdomain.com;
}
```

**No conflict** because:
- Different IPs (192.168.10.1 vs public IP)
- Different ports (8443 vs 443)
- Different server_name directives
- Nginx routes correctly based on IP + Port + Host header

---

## 🌐 Network Topology Details

### Physical Setup

```
┌──────────────────────────────────────────────────────────┐
│                     Internet                             │
└──────────────────────┬───────────────────────────────────┘
                       │
                       │ Public IP
                       │
┌──────────────────────▼───────────────────────────────────┐
│                  Server (Ubuntu)                         │
│                                                          │
│  ┌─────────────────────────────────────────────┐        │
│  │         Network Interface: eth0             │        │
│  │         Role: WAN                           │        │
│  │         IP: DHCP/Static (public)           │        │
│  │         Nginx: Port 443, 80                │        │
│  │         Cert: ZeroSSL (Let's Encrypt)      │        │
│  │         Access: login.yourdomain.com       │        │
│  └─────────────────────────────────────────────┘        │
│                                                          │
│  ┌─────────────────────────────────────────────┐        │
│  │         Network Interface: eth1             │        │
│  │         Role: LAN (Isolated)               │        │
│  │         IP: 192.168.10.1/24               │        │
│  │         Nginx: Port 8443                   │        │
│  │         Cert: mkcert (self-signed)        │        │
│  │         Access: Armory PC only            │        │
│  └─────────────────┬───────────────────────────┘        │
└────────────────────┼──────────────────────────────────────┘
                     │
                     │ Private Network
                     │ 192.168.10.0/24
                     │
┌────────────────────▼──────────────────────────────────────┐
│                  Armory PC                                │
│                  IP: 192.168.10.2/24                     │
│                  Gateway: None (isolated)                │
│                  DNS: None needed                        │
│                  mkcert CA: Installed                    │
└───────────────────────────────────────────────────────────┘
```

---

## 🚀 Step-by-Step Setup

### Prerequisites

- [ ] Server with 2 network interfaces (or VLANs)
- [ ] Public domain name (for WAN)
- [ ] Domain DNS pointing to server public IP
- [ ] Ubuntu 20.04+ or Debian 11+
- [ ] Root access

---

### Step 1: Configure Network Interfaces

```bash
cd /var/www/armguard/deployment/network_setup

# This will configure both interfaces
sudo bash configure-network.sh
```

**What this does:**
- Identifies network interfaces
- Sets up static IP for LAN interface
- Configures routing rules
- No gateway for LAN (isolated)

---

### Step 2: Set Up LAN Network (mkcert)

```bash
sudo bash setup-lan-network.sh
```

**What this does:**
1. Verifies LAN interface (eth1)
2. Sets static IP: 192.168.10.1
3. Installs mkcert
4. Generates self-signed certificates for 192.168.10.1
5. Configures Nginx for LAN (port 8443)
6. Restricts access to Armory PC IP only

**Important Output:**
```
mkcert Root CA Location: /root/.local/share/mkcert
Copy rootCA.pem to Armory PC and install it!
```

**On Armory PC (Windows):**
```powershell
# Copy from server
scp root@192.168.10.1:/root/.local/share/mkcert/rootCA.pem C:\Users\YourUser\

# Double-click rootCA.pem
# Install to: Trusted Root Certification Authorities
```

**On Armory PC (Linux):**
```bash
scp root@192.168.10.1:/root/.local/share/mkcert/rootCA.pem ~/armguard-ca.crt
sudo cp ~/armguard-ca.crt /usr/local/share/ca-certificates/
sudo update-ca-certificates
```

---

### Step 3: Set Up WAN Network (ZeroSSL)

```bash
sudo bash setup-wan-network.sh
```

**Interactive prompts:**
1. Domain name: `login.yourdomain.com`
2. Email: `admin@yourdomain.com`
3. ACME client: `acme.sh` (recommended) or `certbot`

**What this does:**
1. Verifies DNS points to server
2. Installs ACME client (acme.sh or certbot)
3. Obtains SSL certificate from ZeroSSL/Let's Encrypt
4. Configures Nginx for WAN (port 443, 80)
5. Sets up automatic certificate renewal

**ACME Options:**

**Option A: acme.sh (Recommended)**
```bash
# Supports both ZeroSSL and Let's Encrypt
# Faster and more flexible
# Stores certs in: /etc/letsencrypt/live/domain/ (compatible location)
# Auto-renewal: Cron job (daily check)

# Manual renewal
/root/.acme.sh/acme.sh --renew -d login.yourdomain.com --force

# Switch between CAs
/root/.acme.sh/acme.sh --set-default-ca --server letsencrypt
/root/.acme.sh/acme.sh --set-default-ca --server zerossl
```

**Option B: certbot**
```bash
# Official Let's Encrypt client
# Well-tested and documented
# Stores certs in: /etc/letsencrypt/live/domain/
# Auto-renewal: systemd timer (twice daily)

# Manual renewal
certbot renew

# Check renewal status
systemctl status certbot.timer
```

---

### Step 4: Configure Firewall

```bash
sudo bash configure-firewall.sh
```

**Interactive prompts:**
1. SSH access: Both networks / LAN only / WAN only

**What this does:**
1. Resets UFW to defaults
2. Allows LAN traffic from Armory PC only
3. **Blocks LAN subnet from internet access** (critical!)
4. Allows WAN traffic on ports 80, 443
5. Configures connection tracking
6. Enables rate limiting (DDoS protection)
7. Sets up logging

**Firewall Rules Applied:**

```bash
# LAN Rules
ufw allow in on eth1 from 192.168.10.2 to 192.168.10.1 port 8443
ufw deny in on eth1  # Block all other LAN traffic

# WAN Rules
ufw allow in on eth0 to any port 443
ufw allow in on eth0 to any port 80

# Block LAN Internet Access
iptables -I FORWARD -s 192.168.10.0/24 -o eth0 -j DROP
```

---

### Step 5: Verify Setup

```bash
sudo bash verify-network.sh
```

**This tests:**
- ✅ Network interfaces configured
- ✅ SSL certificates present and valid
- ✅ Nginx configuration correct
- ✅ Firewall rules active
- ✅ Ports listening
- ✅ LAN and WAN connectivity
- ✅ Logging configured
- ✅ Auto-renewal enabled

---

## 🔒 Security Features Explained

### 1. Network Isolation

**LAN subnet CANNOT access internet:**
```bash
# iptables FORWARD chain blocks LAN → WAN
iptables -I FORWARD -s 192.168.10.0/24 -o eth0 -j DROP
```

**Why?**
- Prevents armory PC compromise from accessing internet
- Protects against data exfiltration
- Reduces attack surface

### 2. IP-Based Access Control (LAN)

**Only Armory PC can access LAN:**
```nginx
server {
    listen 192.168.10.1:8443;
    
    # Allow only Armory PC
    allow 192.168.10.2;
    
    # Deny everyone else
    deny all;
}
```

### 3. Endpoint Segregation (WAN)

**Admin panel blocked on WAN:**
```nginx
location ~* ^/admin.*$ {
    deny all;
    return 403;
}

location ~* ^/(inventory|transactions|qr-manager).*$ {
    deny all;
    return 403;
}
```

**Personnel can only access:**
- `/login` - Authentication
- `/personnel` - Personnel management
- `/profile` - Personal profile
- `/dashboard` - Limited dashboard

### 4. Rate Limiting

**LAN (Permissive):**
- General: 30 req/s
- Admin: 10 burst
- Armory PC is trusted

**WAN (Strict):**
- General: 5 req/s
- Login: 3 req/min
- API: 20 req/s
- Public internet needs protection

### 5. Connection Limits

**LAN:** 20 connections per IP (Armory PC can have multiple tabs)
**WAN:** 5 connections per IP (prevent abuse)

---

## 📊 Certificate Management

### mkcert (LAN)

**Installation:**
```bash
# On Server
mkcert -install
mkcert -key-file lan-key.pem -cert-file lan-cert.pem 192.168.10.1

# Get CA
cp $(mkcert -CAROOT)/rootCA.pem /tmp/armguard-ca.pem
```

**On Armory PC:**
- Windows: Import to Trusted Root
- Linux: Copy to `/usr/local/share/ca-certificates/`
- macOS: Keychain Access → Import → Trust

**Renewal:** Not needed (valid for 10+ years)

### ZeroSSL/Let's Encrypt (WAN)

**Auto-Renewal:**

**acme.sh:**
```bash
# Check cron
crontab -l | grep acme.sh

# Test renewal
/root/.acme.sh/acme.sh --renew -d login.yourdomain.com --force

# Check logs
cat /root/.acme.sh/login.yourdomain.com/*.log
```

**certbot:**
```bash
# Check timer
systemctl status certbot.timer

# Test renewal
certbot renew --dry-run

# Check logs
journalctl -u certbot
```

**Manual Renewal (if needed):**
```bash
# acme.sh
/root/.acme.sh/acme.sh --renew -d login.yourdomain.com

# certbot
certbot renew
systemctl reload nginx
```

---

## 🧪 Testing the Setup

### Test LAN Network

**From Armory PC:**
```bash
# Test connectivity
ping 192.168.10.1

# Test HTTPS (should work)
curl https://192.168.10.1:8443

# Test internet block (should fail)
ping 8.8.8.8
```

**Expected Results:**
- ✅ Server responds on 192.168.10.1
- ✅ HTTPS with valid certificate
- ❌ Cannot ping internet
- ❌ Cannot access websites

### Test WAN Network

**From any internet device:**
```bash
# Test HTTPS
curl https://login.yourdomain.com

# Try to access admin (should be blocked)
curl https://login.yourdomain.com/admin/
# Expected: 403 Forbidden

# Try personnel login (should work)
curl https://login.yourdomain.com/login/
# Expected: 200 OK
```

### Test Access Control

**From unauthorized device on LAN:**
```bash
# Try to access server (should fail)
curl https://192.168.10.1:8443
# Expected: Connection refused (blocked by Nginx)
```

---

## 📋 Nginx Configuration Deep Dive

### LAN vs WAN Comparison

| Feature | LAN | WAN |
|---------|-----|-----|
| **Bind Address** | 192.168.10.1:8443 | 0.0.0.0:443 |
| **Server Name** | 192.168.10.1 | login.yourdomain.com |
| **SSL Cert** | mkcert self-signed | ZeroSSL public CA |
| **Access Control** | IP whitelist (Armory PC) | Public (rate-limited) |
| **Rate Limiting** | 30 req/s | 5 req/s |
| **Connection Limit** | 20 per IP | 5 per IP |
| **Admin Access** | Allowed | Blocked (403) |
| **Inventory Access** | Allowed | Blocked (403) |
| **Personnel Access** | Allowed | Allowed |
| **Upload Size** | 50M | 5M |
| **Timeouts** | 120s | 60s |

### Custom Headers

Both configs add custom headers to help Django distinguish networks:

```nginx
proxy_set_header X-Network-Type "LAN";   # or "WAN"
```

**In Django views:**
```python
network_type = request.META.get('HTTP_X_NETWORK_TYPE')

if network_type == 'WAN':
    # Restrict to personnel features only
    pass
```

---

## 🔍 Troubleshooting

### Issue: LAN certificate not trusted

**Cause:** mkcert CA not installed on Armory PC

**Solution:**
```bash
# On server, find CA
mkcert -CAROOT

# Copy to Armory PC
scp /root/.local/share/mkcert/rootCA.pem user@192.168.10.2:~/

# On Armory PC (Windows): Double-click → Install to Trusted Root
# On Armory PC (Linux): 
sudo cp ~/rootCA.pem /usr/local/share/ca-certificates/armguard-ca.crt
sudo update-ca-certificates
```

### Issue: WAN certificate fails to obtain

**Cause:** DNS not pointing to server

**Solution:**
```bash
# Check DNS
dig +short login.yourdomain.com

# Should match server public IP
curl ifconfig.me

# Update DNS A record at domain registrar
```

### Issue: Armory PC can access internet

**Cause:** Firewall not blocking LAN forwarding

**Solution:**
```bash
# Check iptables FORWARD chain
sudo iptables -L FORWARD -v -n

# Should see: DROP rule for 192.168.10.0/24

# Re-run firewall script
sudo bash configure-firewall.sh
```

### Issue: Cannot access admin panel on LAN

**Cause:** Wrong Nginx config enabled

**Solution:**
```bash
# Check which configs are enabled
ls -la /etc/nginx/sites-enabled/

# Should see armguard-lan and armguard-wan
# Remove any default config
sudo rm /etc/nginx/sites-enabled/default

# Test and reload
sudo nginx -t
sudo systemctl reload nginx
```

### Issue: Rate limiting too strict

**Cause:** Default limits may be too low for your use case

**Solution:**
```bash
# Edit Nginx config
sudo nano /etc/nginx/sites-available/armguard-wan

# Increase rate
# limit_req_zone ... rate=10r/s;  # was 5r/s

# Test and reload
sudo nginx -t
sudo systemctl reload nginx
```

---

## 📚 Additional Resources

### Log Locations

```bash
# LAN Nginx logs
/var/log/nginx/armguard_lan_access.log
/var/log/nginx/armguard_lan_error.log

# WAN Nginx logs
/var/log/nginx/armguard_wan_access.log
/var/log/nginx/armguard_wan_error.log

# Firewall logs
/var/log/ufw.log

# ACME logs (acme.sh)
/root/.acme.sh/login.yourdomain.com/*.log

# ACME logs (certbot)
/var/log/letsencrypt/
```

### Monitoring Commands

```bash
# Watch LAN access in real-time
sudo tail -f /var/log/nginx/armguard_lan_access.log

# Watch WAN access
sudo tail -f /var/log/nginx/armguard_wan_access.log

# Monitor firewall blocks
sudo tail -f /var/log/ufw.log | grep BLOCK

# Check rate limiting
sudo grep "limiting" /var/log/nginx/armguard_wan_error.log

# Check SSL certificate expiry
openssl x509 -in /etc/letsencrypt/live/login.yourdomain.com/fullchain.pem -noout -enddate
```

---

## ✅ Security Checklist

- [ ] LAN network isolated (cannot access internet)
- [ ] Only Armory PC can access LAN
- [ ] WAN admin panel blocked
- [ ] WAN inventory endpoints blocked
- [ ] SSL certificates valid (both LAN and WAN)
- [ ] Firewall active and rules correct
- [ ] Auto-renewal configured (WAN)
- [ ] Rate limiting active
- [ ] Logging enabled
- [ ] mkcert CA installed on Armory PC
- [ ] DNS pointing to server (WAN)
- [ ] Both networks tested and accessible

---

## 🎓 Understanding the Security Model

### Defense in Depth

This setup implements multiple security layers:

1. **Network Layer**: Physical isolation (different interfaces)
2. **Firewall Layer**: iptables/UFW blocks unwanted traffic
3. **Application Layer**: Nginx IP restrictions and endpoint blocking
4. **Transport Layer**: TLS encryption (both networks)
5. **Authentication Layer**: Django user authentication
6. **Authorization Layer**: Role-based access control

### Attack Surface Analysis

**LAN Network:**
- Attack surface: Minimal (single trusted device)
- Threat model: Compromised Armory PC
- Mitigations: Network isolation, no internet access

**WAN Network:**
- Attack surface: Internet (global)
- Threat model: DDoS, brute force, exploits
- Mitigations: Rate limiting, endpoint blocking, public CA, monitoring

---

**This hybrid setup provides enterprise-grade security for ArmGuard! 🛡️**
