**Automated setup with full security hardening**

```bash
# SSH to your server
ssh rds@192.168.0.10

# Clone/update repository
cd ARMGUARD_RDS_v.2
git pull origin main

# Run VPN setup script
sudo ./deployment/setup-vpn-server.sh
```

**Manual Configuration Steps:**
1. **Router Setup**: Forward port 51820 (UDP) to 192.168.0.10
2. **Get Public IP**: `curl ifconfig.me` or check router admin page
3. **Update Client Configs**: Replace YOUR_PUBLIC_IP in client files
4. **Distribute Configs**: Send client .conf files securely

**Client Setup:**
- **Windows**: Import .conf file to WireGuard app
- **Android/iOS**: Scan QR code with WireGuard app
- **Linux**: `sudo wg-quick up client.conf`

### 2. SSH Tunnel Access

**For Linux/macOS Users:**
```bash
# Download client script
wget https://raw.githubusercontent.com/Stealth3535/ARMGUARD_RDS_v.2/main/deployment/ssh-tunnel-client.sh
chmod +x ssh-tunnel-client.sh

# Create tunnel (interactive mode)
./ssh-tunnel-client.sh

# Or direct command
./ssh-tunnel-client.sh connect YOUR_PUBLIC_IP
```

**For Windows Users:**
```powershell
# Download PowerShell script
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/Stealth3535/ARMGUARD_RDS_v.2/main/deployment/ssh-tunnel-client.ps1" -OutFile "ssh-tunnel-client.ps1"

# Run interactive mode
.\ssh-tunnel-client.ps1

# Or direct command
.\ssh-tunnel-client.ps1 -ServerIP YOUR_PUBLIC_IP -Action connect
```

**Router Configuration:**
- Forward port 22 (SSH) to 192.168.0.10
- Or use alternative SSH port for security

### 3. HTTPS Direct Access (⚠️ High Risk)

**Only use when VPN/SSH is not possible!**

```bash
# SSH to server  
ssh rds@192.168.0.10

# Run HTTPS setup with security hardening
sudo ./deployment/setup-https-direct.sh
```

**Router Configuration:**
- Forward port 8443 (HTTPS) to 192.168.0.10
- Forward port 80 (HTTP) to 192.168.0.10 (for redirect)

**Security Monitoring:**
```bash
# Check fail2ban status
sudo fail2ban-client status

# Monitor access logs
sudo tail -f /var/log/nginx/access.log

# Check for attacks
sudo fail2ban-client status nginx-badbots
```

---

## 🔧 Router Configuration Guide

### Finding Your Router Admin Panel
1. Open browser to: `192.168.1.1` or `192.168.0.1`
2. Use router admin credentials (usually on router label)

### Port Forwarding Rules
| Service | External Port | Internal IP | Internal Port | Protocol |
|---------|-------------- |-------------|---------------|----------|
| VPN     | 51820         | 192.168.0.10| 51820         | UDP      |
| SSH     | 22            | 192.168.0.10| 22            | TCP      |
| HTTPS   | 8443          | 192.168.0.10| 8443          | TCP      |
| HTTP    | 80            | 192.168.0.10| 80            | TCP      |

### Alternative SSH Port (Security)
```bash
# Change SSH port on server
sudo nano /etc/ssh/sshd_config
# Change: Port 22 to Port 2222
sudo systemctl restart ssh

# Forward port 2222 instead of 22 on router
```

---

## 🛡️ Security Hardening

### Server Security Checklist

**Essential Security Measures:**
- [ ] Strong passwords enforced
- [ ] SSH key authentication enabled
- [ ] Firewall (ufw) configured
- [ ] Fail2ban installed and configured
- [ ] Regular system updates scheduled
- [ ] Log monitoring enabled
- [ ] Backup strategy implemented

**Advanced Security:**
```bash
# Disable SSH password authentication
sudo nano /etc/ssh/sshd_config
# Set: PasswordAuthentication no
# Set: PermitRootLogin no

# Enable automatic updates
sudo apt install unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades

# Install intrusion detection
sudo apt install rkhunter chkrootkit
```

### Network Security

**Router Security:**
- Change default admin password
- Disable WPS
- Use WPA3/WPA2 encryption
- Enable guest network for isolation
- Disable unnecessary services

**Firewall Rules:**
```bash
# Default deny everything
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow only necessary ports
sudo ufw allow ssh
sudo ufw allow 51820/udp  # VPN
sudo ufw allow 8443/tcp   # HTTPS (if using)

# Enable firewall
sudo ufw enable
```

---

## 📱 Client Applications

### VPN Clients
- **Windows**: WireGuard for Windows
- **macOS**: WireGuard for macOS
- **iOS**: WireGuard (App Store)
- **Android**: WireGuard (Play Store)
- **Linux**: wireguard-tools package

### SSH Clients
- **Windows**: Built-in OpenSSH, PuTTY, MobaXterm
- **macOS**: Built-in SSH
- **iOS**: Termius, Prompt 3
- **Android**: JuiceSSH, Termux

---

## 🚨 Troubleshooting

### Common Issues

**VPN Connection Issues:**
```bash
# Check server status
sudo systemctl status wg-quick@wg0

# Check firewall
sudo ufw status

# Check logs
sudo journalctl -u wg-quick@wg0
```

**SSH Tunnel Issues:**
```bash
# Test SSH connection first
ssh -v rds@YOUR_PUBLIC_IP

# Check if port is available
netstat -an | grep 8000

# Kill existing tunnels
pkill -f "ssh.*-L"
```

**HTTPS Direct Access Issues:**
```bash
# Check ArmGuard service
sudo systemctl status armguard

# Check Nginx
sudo systemctl status nginx

# View error logs
sudo tail -f /var/log/nginx/error.log
```

### Performance Optimization

**For High Traffic:**
```bash
# Increase Nginx worker processes
sudo nano /etc/nginx/nginx.conf
# Set: worker_processes auto;

# Optimize Django settings
# Add to settings_production.py:
DATABASES['default']['CONN_MAX_AGE'] = 60
ALLOWED_HOSTS = ['*']  # Only for direct HTTPS
```

---

## 📊 Monitoring and Maintenance

### Regular Maintenance Tasks

**Weekly:**
- Check system logs: `sudo journalctl --since "1 week ago"`
- Monitor disk usage: `df -h`
- Check for security updates: `sudo apt list --upgradable`

**Monthly:**
- Rotate SSL certificates (if Let's Encrypt)
- Review fail2ban logs: `sudo fail2ban-client status`
- Check VPN client usage: `sudo wg show`
- Backup configuration files

**Quarterly:**
- Security audit and penetration testing
- Update VPN client configurations
- Review access logs for anomalies
- Update documentation

### Automated Monitoring Script

```bash
#!/bin/bash
# Save as /home/rds/monitor-armguard.sh

echo "🔍 ArmGuard Health Check - $(date)"
echo "=================================="

# Check services
echo "📋 Service Status:"
systemctl is-active --quiet armguard && echo "✅ ArmGuard: Running" || echo "❌ ArmGuard: Stopped"
systemctl is-active --quiet nginx && echo "✅ Nginx: Running" || echo "❌ Nginx: Stopped"
systemctl is-active --quiet fail2ban && echo "✅ Fail2ban: Running" || echo "❌ Fail2ban: Stopped"

# Check disk space
echo -e "\n💾 Disk Usage:"
df -h / | tail -n 1 | awk '{print "Root: " $5 " used"}'

# Check memory
echo -e "\n🧠 Memory Usage:"
free -h | grep Mem | awk '{print "RAM: " $3 "/" $2}'

# Check fail2ban status
echo -e "\n🚨 Security Status:"
fail2ban-client status | grep "Number of jail:" | awk '{print "Active Jails: " $4}'

echo -e "\n✅ Health check complete"
```

**Setup monitoring cron job:**
```bash
chmod +x /home/rds/monitor-armguard.sh
crontab -e
# Add: 0 */6 * * * /home/rds/monitor-armguard.sh >> /home/rds/health.log
```

---

## 🎯 Recommended Deployment Strategy

Based on your security needs:

### **High Security (Recommended)**
1. **Deploy VPN Server** for secure access
2. **Keep ArmGuard internal** (no direct internet exposure)
3. **Use SSH as backup** for emergency access
4. **Enable comprehensive monitoring**

### **Medium Security**
1. **Use SSH Tunneling** for primary access
2. **Configure basic firewall** protection
3. **Enable fail2ban** for attack protection
4. **Regular security updates**

### **Low Security (Not Recommended)**
1. **HTTPS Direct Access** only if absolutely necessary
2. **Implement ALL security hardening** measures
3. **Continuous monitoring** required
4. **Regular penetration testing**

---

## 📞 Support and Updates

- **GitHub Repository**: https://github.com/Stealth3535/ARMGUARD_RDS_v.2
- **Issues**: Create GitHub issues for bugs or feature requests
- **Security Updates**: Monitor repository for security patches

**Emergency Recovery:**
```bash
# If web interface becomes unresponsive
sudo systemctl restart armguard nginx

# If VPN stops working
sudo systemctl restart wg-quick@wg0

# If system is compromised
sudo ufw reset  # Reset firewall
sudo fail2ban-client reload  # Reload protection
```

Remember: **Security is an ongoing process, not a one-time setup!**