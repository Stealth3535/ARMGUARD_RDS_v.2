# 🌐 ArmGuard Secure Hybrid Network Setup

## Overview

This network setup provides **complete isolation** between:
- **LAN**: Secure internal communication (Server ↔ Armory PC)
- **WAN**: Public personnel login portal

---

## 📋 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    ARMGUARD SERVER                          │
│                                                             │
│  ┌─────────────────┐              ┌────────────────────┐    │
│  │   LAN Network   │              │    WAN Network     │    │
│  │  192.168.10.x   │              │  Public Internet   │    │
│  │                 │              │                    │    │
│  │  • mkcert SSL   │              │  • ZeroSSL/LE      │    │
│  │  • Port 8443    │              │  • Port 443        │    │
│  │  • Armory Only  │              │  • Public Access   │    │
│  └─────────────────┘              └────────────────────┘    │
│          ↕                                  ↕               │
│    Armory PC Only               Personnel (Worldwide)       │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 Network Topology

### LAN Network (192.168.10.0/24)
- **Server IP**: `192.168.10.1`
- **Armory PC**: `192.168.10.2`
- **Protocol**: HTTPS (port 8443)
- **Certificate**: mkcert (self-signed)
- **Access**: Restricted to Armory PC only
- **Use Case**: Inventory management, secure transactions

### WAN Network (Public)
- **Server IP**: Public IP or domain
- **Domain**: `login.yourdomain.com`
- **Protocol**: HTTPS (port 443)
- **Certificate**: ZeroSSL (ACME)
- **Access**: Internet-facing personnel portal
- **Use Case**: Remote login, personnel management

---

## 🔐 Security Model

### 1. Network Isolation
- LAN subnet **CANNOT** access internet
- WAN traffic **CANNOT** access LAN resources
- Firewall enforces strict separation

### 2. Certificate Strategy
- **LAN**: mkcert self-signed (trusted locally)
- **WAN**: ZeroSSL/Let's Encrypt (publicly trusted)
- No certificate conflicts

### 3. Access Control
- **LAN**: IP-based restrictions (Armory PC only)
- **WAN**: Django authentication + rate limiting
- Separate Nginx server blocks

---

## 📚 Quick Start

### 1. Configure Network Interfaces
```bash
sudo bash network_setup/configure-network.sh
```

### 2. Set Up LAN (mkcert)
```bash
sudo bash network_setup/setup-lan-network.sh
```

### 3. Set Up WAN (ZeroSSL)
```bash
sudo bash network_setup/setup-wan-network.sh
```

### 4. Configure Firewall
```bash
sudo bash network_setup/configure-firewall.sh
```

### 5. Verify Setup
```bash
sudo bash network_setup/verify-network.sh
```

---

## 📁 Files in This Directory

| File | Purpose |
|------|---------|
| **configure-network.sh** | Initial network interface setup |
| **setup-lan-network.sh** | LAN network with mkcert SSL |
| **setup-wan-network.sh** | WAN network with ZeroSSL |
| **configure-firewall.sh** | Complete firewall rules (ufw/iptables) |
| **verify-network.sh** | Test and verify setup |
| **nginx-lan.conf** | Nginx config for LAN |
| **nginx-wan.conf** | Nginx config for WAN |
| **firewall-rules.sh** | Detailed firewall rules |
| **HYBRID_NETWORK_GUIDE.md** | Complete setup guide |

---

## ⚠️ Important Notes

1. **Two Network Interfaces Required**
   - One for LAN (private subnet)
   - One for WAN (public internet)

2. **Domain Name Required for WAN**
   - Must own domain for ZeroSSL
   - DNS must point to server public IP

3. **Armory PC Configuration**
   - Install mkcert root CA
   - Configure static IP: 192.168.10.2
   - Access LAN via: https://192.168.10.1:8443

4. **Personnel Access**
   - Access via: https://login.yourdomain.com
   - Public internet connectivity required

---

## 🔒 Security Features

- ✅ Complete LAN/WAN isolation
- ✅ IP-based access control (LAN)
- ✅ Rate limiting (both networks)
- ✅ Automatic certificate renewal (WAN)
- ✅ Encrypted traffic (both networks)
- ✅ Firewall protection
- ✅ Separate logging per network
- ✅ Role-based access control

---

## 📊 Port Allocation

| Port | Network | Purpose | Access |
|------|---------|---------|--------|
| 8443 | LAN | Armory interface | Armory PC only |
| 443 | WAN | Personnel portal | Public internet |
| 80 | WAN | HTTP redirect | Public (redirects to 443) |

---

## 🚨 Troubleshooting

See [HYBRID_NETWORK_GUIDE.md](HYBRID_NETWORK_GUIDE.md) for:
- Detailed configuration steps
- Troubleshooting common issues
- Testing procedures
- Certificate management
- Firewall debugging

---

## 📞 Support

For issues with:
- **Network Configuration**: Check interface settings in configure-network.sh
- **Certificates**: Run verify-network.sh
- **Firewall**: Review firewall-rules.sh output
- **Access Issues**: Check Nginx error logs per network
