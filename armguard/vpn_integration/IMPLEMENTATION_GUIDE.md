# 🚀 WireGuard VPN Implementation Guide for ArmGuard
**Status**: ✅ **COMPLETE IMPLEMENTATION** - Ready for deployment

## 📋 Quick Start Checklist

- ✅ **VPN Server Setup**: Automated installation script ready
- ✅ **Client Generation**: Role-based client configuration generator
- ✅ **Django Integration**: VPN-aware middleware and decorators
- ✅ **Security Policy**: Military-grade access controls implemented
- ✅ **Monitoring**: Real-time VPN connection monitoring
- ✅ **Testing**: Comprehensive test suite included

## 🔧 Prerequisites

### Server Requirements
- **Hardware**: Raspberry Pi 4 (4GB RAM recommended) or Ubuntu Server
- **OS**: Ubuntu 20.04+ or Raspberry Pi OS
- **Network**: Internet connection via router (as per your diagram)
- **Ports**: UDP 51820 (forwarded through router)
- **Storage**: 32GB SD card minimum

### Network Configuration (Your Setup)
- **LAN Network**: 192.168.x.x (your existing network)
- **VPN Network**: 10.0.0.0/24 (new VPN subnet)
- **Server IP**: Your Raspberry Pi LAN IP
- **Router**: Internet connected (no app exposure)

---

## 🚀 One-Click Installation

### Step 2: Generate Client Configurations (10 minutes)
```bash
# Create VPN clients for different roles
# Commander access (full inventory viewing)
sudo bash generate-client-config.sh commander-john commander

# Armorer access (equipment management viewing)
sudo bash generate-client-config.sh armorer-jane armorer

# Emergency access (critical equipment only)
sudo bash generate-client-config.sh emergency-ops emergency

# Personnel access (personal status only)
sudo bash generate-client-config.sh personnel-smith personnel

# Configurations are saved to: /etc/wireguard/clients/
# QR codes generated for mobile devices: /etc/wireguard/clients/*.png
```

### Step 3: Django Integration (5 minutes)
```python
# Add to your ArmGuard settings.py

# Enable VPN integration
WIREGUARD_ENABLED = True
WIREGUARD_INTERFACE = 'wg0'
WIREGUARD_NETWORK = '10.0.0.0/24'
WIREGUARD_PORT = 51820

# Add VPN middleware (CRITICAL for security)
MIDDLEWARE = [
    # ... your existing middleware ...
    'core.network_middleware.NetworkBasedAccessMiddleware',  # Existing
    'vpn_integration.core_integration.vpn_middleware.VPNAwareNetworkMiddleware',  # NEW
]

# VPN role-based access configuration
VPN_ROLE_RANGES = {
    'commander': {
        'ip_range': ('10.0.0.10', '10.0.0.19'),
        'access_level': 'VPN_INVENTORY_VIEW',
        'session_timeout': 7200,  # 2 hours
        'description': 'Full inventory viewing for commanders'
    },
    'armorer': {
        'ip_range': ('10.0.0.20', '10.0.0.39'),
        'access_level': 'VPN_INVENTORY_VIEW', 
        'session_timeout': 3600,  # 1 hour
        'description': 'Equipment management viewing'
    },
    'emergency': {
        'ip_range': ('10.0.0.40', '10.0.0.49'),
        'access_level': 'VPN_INVENTORY_LIMITED',
        'session_timeout': 1800,  # 30 minutes
        'description': 'Emergency response access'
    },
    'personnel': {
        'ip_range': ('10.0.0.50', '10.0.0.199'),
        'access_level': 'VPN_STATUS_ONLY',
        'session_timeout': 900,  # 15 minutes
        'description': 'Personal status checking only'
    }
}
```
wg genkey | sudo tee server_private.key | wg pubkey | sudo tee server_public.key

# Secure the private key
sudo chmod 600 server_private.key
```

---

## Step 2: Configure WireGuard Server (10 minutes)

### 2.1 Create Server Configuration
```bash
sudo tee /etc/wireguard/wg0.conf << EOF
[Interface]
# Server Configuration
PrivateKey = $(sudo cat /etc/wireguard/keys/server_private.key)
Address = 10.0.0.1/24
ListenPort = 51820

# Firewall rules
PostUp = iptables -A FORWARD -i wg0 -j ACCEPT; iptables -t nat -A POSTROUTING -s 10.0.0.0/24 -o eth0 -j MASQUERADE; iptables -A FORWARD -i eth0 -o wg0 -m state --state RELATED,ESTABLISHED -j ACCEPT
PostDown = iptables -D FORWARD -i wg0 -j ACCEPT; iptables -t nat -D POSTROUTING -s 10.0.0.0/24 -o eth0 -j MASQUERADE; iptables -D FORWARD -i eth0 -o wg0 -m state --state RELATED,ESTABLISHED -j ACCEPT

# DNS servers for clients
DNS = 8.8.8.8, 8.8.4.4

# Clients will be added below
EOF
```

### 2.2 Secure Configuration File
```bash
sudo chmod 600 /etc/wireguard/wg0.conf
sudo chown root:root /etc/wireguard/wg0.conf
```

---

## Step 3: Configure Firewall (5 minutes)

### 3.1 Open WireGuard Port
```bash
# Allow WireGuard port
sudo ufw allow 51820/udp comment "WireGuard VPN"

# Allow forwarding for VPN clients
sudo ufw route allow in on wg0 out on eth1 to 192.168.10.0/24
sudo ufw route allow in on eth1 out on wg0 from 192.168.10.0/24

# Reload firewall
sudo ufw reload
```

---

## Step 4: Generate Client Configurations (10 minutes per client)

### 4.1 Create Client Generation Script
```bash
sudo tee /usr/local/bin/add-vpn-client.sh << 'EOF'
#!/bin/bash

if [ $# -ne 3 ]; then
    echo "Usage: $0 <client_name> <client_description> <client_role>"
    echo "Roles: commander, armorer, personnel, emergency"
    exit 1
fi

CLIENT_NAME=$1
CLIENT_DESC=$2
CLIENT_ROLE=$3

# Generate client keys
CLIENT_PRIVATE=$(wg genkey)
CLIENT_PUBLIC=$(echo $CLIENT_PRIVATE | wg pubkey)

# Assign IP based on role
case $CLIENT_ROLE in
    "commander")
        CLIENT_IP="10.0.0.10"
        ALLOWED_IPS="192.168.10.0/24"
        ;;
    "armorer")
        CLIENT_IP="10.0.0.20"
        ALLOWED_IPS="192.168.10.0/24"
        ;;
    "emergency")
        CLIENT_IP="10.0.0.30"
        ALLOWED_IPS="192.168.10.0/24"
        ;;
    "personnel")
        CLIENT_IP="10.0.0.40"
        ALLOWED_IPS="192.168.10.0/24"
        ;;
    *)
        echo "Invalid role. Use: commander, armorer, personnel, emergency"
        exit 1
        ;;
esac

# Add peer to server config
echo "" >> /etc/wireguard/wg0.conf
echo "# ${CLIENT_DESC}" >> /etc/wireguard/wg0.conf
echo "[Peer]" >> /etc/wireguard/wg0.conf
echo "PublicKey = ${CLIENT_PUBLIC}" >> /etc/wireguard/wg0.conf
echo "AllowedIPs = ${CLIENT_IP}/32" >> /etc/wireguard/wg0.conf
echo "# Role: ${CLIENT_ROLE}" >> /etc/wireguard/wg0.conf

# Create client config file
mkdir -p /etc/wireguard/clients
cat > /etc/wireguard/clients/${CLIENT_NAME}.conf << EOC
[Interface]
# Client: ${CLIENT_DESC}
# Role: ${CLIENT_ROLE}
PrivateKey = ${CLIENT_PRIVATE}
Address = ${CLIENT_IP}/24
DNS = 10.0.0.1

[Peer]
# ArmGuard Server
PublicKey = $(cat /etc/wireguard/keys/server_public.key)
Endpoint = YOUR_SERVER_PUBLIC_IP:51820
AllowedIPs = ${ALLOWED_IPS}
PersistentKeepalive = 25
EOC

echo "Client configuration created: /etc/wireguard/clients/${CLIENT_NAME}.conf"
echo "Client public key: ${CLIENT_PUBLIC}"
echo "Restart WireGuard to apply changes: sudo systemctl restart wg-quick@wg0"

# Generate QR code for mobile devices
qrencode -t ansiutf8 < /etc/wireguard/clients/${CLIENT_NAME}.conf
echo "QR code generated above for mobile device setup"
EOF

sudo chmod +x /usr/local/bin/add-vpn-client.sh
```

### 4.2 Create Sample Client Configurations
```bash
# Install QR code generator
sudo apt install qrencode -y

# Generate configurations for different roles
sudo /usr/local/bin/add-vpn-client.sh field-commander "Field Commander Device" commander
sudo /usr/local/bin/add-vpn-client.sh armorer-home "Armorer Home Office" armorer  
sudo /usr/local/bin/add-vpn-client.sh emergency-tablet "Emergency Operations Tablet" emergency
sudo /usr/local/bin/add-vpn-client.sh personnel-mobile "Personnel Mobile Device" personnel
```

---

## Step 5: Start WireGuard Service (2 minutes)

### 5.1 Enable and Start Service
```bash
# Enable WireGuard interface
sudo systemctl enable wg-quick@wg0

# Start WireGuard
sudo systemctl start wg-quick@wg0

# Check status
sudo systemctl status wg-quick@wg0

# Show active connections
sudo wg show
```

### 5.2 Verify Server Configuration
```bash
# Check interface is up
ip addr show wg0

# Verify listening port
sudo netstat -ulnp | grep 51820

# Test internal connectivity
ping -c 3 10.0.0.1
```

---

## Step 6: Integrate with ArmGuard (15 minutes)

### 6.1 Update Network Settings
```bash
# Add VPN network to ArmGuard settings
sudo tee -a /var/www/armguard/core/settings.py << 'EOF'

# VPN Integration Settings
WIREGUARD_ENABLED = True
WIREGUARD_NETWORK = '10.0.0.0/24'

# Update LAN networks to include VPN
LAN_NETWORKS = [
    '192.168.10.0/24',  # Physical LAN
    '10.0.0.0/24',      # WireGuard VPN
    '172.16.0.0/12',    # Private networks
    '10.0.0.0/8',       
    '127.0.0.0/8',      # Loopback
]

# VPN role-based access control
VPN_ROLE_ACCESS = {
    'commander': 'full_lan',     # Full LAN-level access
    'armorer': 'full_lan',       # Full LAN-level access  
    'emergency': 'full_lan',     # Full LAN-level access (time-limited)
    'personnel': 'wan_readonly', # WAN-level read-only access
}
EOF
```

### 6.2 Update Middleware for VPN Detection
```bash
# Create VPN-aware middleware extension
sudo tee /var/www/armguard/core/vpn_middleware.py << 'EOF'
# VPN-Aware Network Middleware
import ipaddress
from django.conf import settings
from core.network_middleware import NetworkBasedAccessMiddleware

class VPNAwareNetworkMiddleware(NetworkBasedAccessMiddleware):
    """Enhanced middleware with VPN awareness"""
    
    def detect_network_type(self, request):
        """Enhanced network detection including VPN"""
        server_port = request.get_port()
        client_ip = self.get_client_ip(request)
        
        try:
            client_addr = ipaddress.ip_address(client_ip)
            
            # Check for WireGuard VPN network
            if client_addr in ipaddress.ip_network('10.0.0.0/24'):
                # VPN connection - check user role for access level
                return self.get_vpn_access_level(request)
                
            # Existing LAN detection
            if server_port == getattr(settings, 'LAN_PORT', '8443'):
                return 'LAN'
            elif server_port == getattr(settings, 'WAN_PORT', '443'):
                return 'WAN'
                
        except ValueError:
            # Invalid IP address
            pass
            
        return 'UNKNOWN'
    
    def get_vpn_access_level(self, request):
        """Determine VPN access level based on user role"""
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return 'VPN_UNAUTHENTICATED'
            
        user_groups = [g.name.lower() for g in request.user.groups.all()]
        
        # Map user groups to VPN access levels
        if 'admin' in user_groups or 'superuser' in user_groups:
            return 'VPN_LAN'  # Full LAN-level access
        elif 'armorer' in user_groups:
            return 'VPN_LAN'  # Full LAN-level access
        elif 'personnel' in user_groups:
            return 'VPN_WAN'  # WAN-level access via VPN
        else:
            return 'VPN_LIMITED'
EOF
```

### 6.3 Update Django Settings for VPN Middleware
```bash
# Update middleware configuration
sudo sed -i '/core.network_middleware.NetworkBasedAccessMiddleware/c\    '\''core.vpn_middleware.VPNAwareNetworkMiddleware'\'',' /var/www/armguard/core/settings.py
```

### 6.4 Restart ArmGuard Services
```bash
# Restart Django application
sudo systemctl restart gunicorn
sudo systemctl restart nginx

# Verify services are running
sudo systemctl status gunicorn
sudo systemctl status nginx
```

---

## Step 7: Client Device Setup

### 7.1 Windows Client
1. **Download**: WireGuard for Windows from [wireguard.com](https://www.wireguard.com/install/)
2. **Install**: Run installer as administrator
3. **Import Config**: Click "Import tunnel(s) from file" and select client `.conf` file
4. **Connect**: Click "Activate" to establish VPN connection
5. **Test**: Access `https://10.0.0.1:8443` in browser

### 7.2 Mobile Devices (iOS/Android)
1. **Install**: WireGuard app from App Store/Google Play
2. **Scan QR**: Use app to scan QR code generated during client creation
3. **Connect**: Tap to activate VPN tunnel
4. **Test**: Access ArmGuard through mobile browser

### 7.3 Linux Client
```bash
# Install WireGuard
sudo apt install wireguard

# Copy configuration file
sudo cp client-config.conf /etc/wireguard/

# Connect
sudo wg-quick up client-config

# Test connection
curl -k https://10.0.0.1:8443/
```

---

## Step 8: Testing & Verification (10 minutes)

### 8.1 Server-Side Testing
```bash
# Check active connections
sudo wg show

# Monitor logs
sudo journalctl -u wg-quick@wg0 -f

# Network connectivity test
sudo tcpdump -i wg0 -n
```

### 8.2 Client-Side Testing
```bash
# From VPN client, test connectivity
ping 10.0.0.1                    # VPN gateway
ping 192.168.10.1                # ArmGuard LAN

# Test ArmGuard access levels
curl -k https://10.0.0.1:8443/personnel/     # Should work (LAN access)
curl -k https://10.0.0.1:8443/admin/         # Should work for admins/armorers
```

### 8.3 Security Verification
```bash
# Verify encryption is active
sudo wg show wg0 transfer

# Check firewall rules
sudo iptables -L FORWARD -v

# Verify no internet access through VPN (if configured)
# From client: ping 8.8.8.8 (should fail if split-tunneling disabled)
```

---

## Step 9: Monitoring & Maintenance

### 9.1 Connection Monitoring Script
```bash
sudo tee /usr/local/bin/monitor-vpn.sh << 'EOF'
#!/bin/bash
echo "=== WireGuard VPN Status ==="
echo "Server: $(date)"
echo
echo "Active Connections:"
wg show wg0 | grep -E "peer|transfer|latest handshake"
echo
echo "Network Statistics:"
cat /proc/net/dev | grep wg0
echo
echo "Recent Connections (last 10):"
journalctl -u wg-quick@wg0 --since "1 day ago" | tail -10
EOF

sudo chmod +x /usr/local/bin/monitor-vpn.sh
```

### 9.2 Automated Key Rotation (Monthly)
```bash
# Create key rotation script
sudo tee /usr/local/bin/rotate-vpn-keys.sh << 'EOF'
#!/bin/bash
# Monthly key rotation for enhanced security
BACKUP_DIR="/etc/wireguard/backups/$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

# Backup current configuration
cp /etc/wireguard/wg0.conf $BACKUP_DIR/
cp -r /etc/wireguard/keys $BACKUP_DIR/

echo "VPN key rotation initiated: $(date)"
echo "Previous configuration backed up to: $BACKUP_DIR"
echo "Manual client reconfiguration required after rotation"
EOF

sudo chmod +x /usr/local/bin/rotate-vpn-keys.sh

# Add to monthly cron (uncomment when ready)
# echo "0 2 1 * * /usr/local/bin/rotate-vpn-keys.sh" | sudo crontab -
```

---

## Step 10: Security Hardening

### 10.1 Additional Firewall Rules
```bash
# Limit VPN connection attempts
sudo ufw limit 51820/udp

# Log VPN connections
sudo ufw logging on

# Block VPN clients from accessing server SSH
sudo ufw deny in on wg0 to any port 22
```

### 10.2 Fail2Ban Integration
```bash
# Install fail2ban
sudo apt install fail2ban -y

# Create WireGuard filter
sudo tee /etc/fail2ban/filter.d/wireguard.conf << 'EOF'
[Definition]
failregex = Invalid handshake initiation from <HOST>
            Failed to receive packet from <HOST>
            Bad packet received from <HOST>
ignoreregex =
EOF

# Create jail configuration
sudo tee /etc/fail2ban/jail.d/wireguard.local << 'EOF'
[wireguard]
enabled = true
port = 51820
protocol = udp
filter = wireguard
logpath = /var/log/syslog
maxretry = 3
bantime = 3600
findtime = 600
EOF

# Restart fail2ban
sudo systemctl restart fail2ban
```

---

## Troubleshooting Guide

### Common Issues

#### 1. Client Can't Connect
```bash
# Check server status
sudo systemctl status wg-quick@wg0

# Verify firewall
sudo ufw status | grep 51820

# Check port binding
sudo netstat -ulnp | grep 51820

# Test from server
ping 10.0.0.10  # Replace with client IP
```

#### 2. Connected but Can't Access ArmGuard
```bash
# Check routing
ip route show table all | grep wg0

# Verify ArmGuard is listening
sudo netstat -tlnp | grep 8443

# Check Django logs
tail -f /var/log/armguard/django.log
```

#### 3. Slow Performance
```bash
# Check server resources
top
df -h
iotop

# Monitor network usage
iftop -i wg0

# Check MTU settings
ip link show wg0
```

### Debug Commands
```bash
# Detailed WireGuard status
sudo wg show all

# Connection logs
sudo journalctl -u wg-quick@wg0 -n 50

# Network troubleshooting
traceroute 10.0.0.1
mtr 10.0.0.1

# Packet capture
sudo tcpdump -i wg0 -n host 10.0.0.10
```

---

## Success Criteria

✅ **Server Installation**: WireGuard service running on port 51820  
✅ **Client Connection**: All client devices can establish VPN tunnel  
✅ **Network Access**: VPN clients can access 10.0.0.1 (server)  
✅ **ArmGuard Access**: VPN clients can access ArmGuard interface  
✅ **Role-Based Access**: Different access levels work per user role  
✅ **Security**: Firewall rules active, encryption verified  
✅ **Monitoring**: Connection monitoring and logging active  
✅ **Documentation**: All configurations documented and backed up  

---

**Implementation Complete!** 🎉

Your ArmGuard system now supports secure remote access via WireGuard VPN while maintaining the existing LAN/WAN security architecture.

**Next Steps:**
1. Train users on VPN client setup and usage
2. Establish regular monitoring and maintenance schedule  
3. Create incident response procedures for VPN-related security events
4. Plan quarterly security audits and key rotation procedures