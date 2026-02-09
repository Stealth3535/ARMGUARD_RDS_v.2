# SSH Setup Guide for 192.168.0.1
# Complete instructions to enable SSH on your target server

## Current Status:
- ✅ Host `192.168.0.1` is reachable (ping successful)  
- ❌ SSH service (port 22) is not running
- 🎯 Goal: Enable SSH to control and deploy ArmGuard

---

## Step 1: Identify Your System Type

Your server at `192.168.0.1` needs SSH enabled. First, determine what type of system it is:

### Check if it has a Web Interface
Open your web browser and try:
- **http://192.168.0.1** 
- **https://192.168.0.1**

If you get a web interface, it might be:
- Router/Network device admin panel
- Linux server with web management  
- IoT device with configuration interface

---

## Step 2: Enable SSH Based on System Type

### 🐧 **Linux Server (Ubuntu/Debian/CentOS/RHEL)**

**Option A: Physical Access (Recommended)**
1. Connect keyboard & monitor to `192.168.0.1`
2. Login locally 
3. Run these commands:

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install openssh-server -y
sudo systemctl enable ssh
sudo systemctl start ssh
sudo ufw allow ssh

# RHEL/CentOS/Fedora  
sudo dnf install openssh-server -y    # or: yum install openssh-server -y
sudo systemctl enable sshd
sudo systemctl start sshd
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --reload

# Check if SSH is running
sudo systemctl status ssh      # Ubuntu/Debian
sudo systemctl status sshd     # RHEL/CentOS/Fedora
```

**Option B: If System Has VNC/Remote Desktop**
1. Connect via VNC viewer or Remote Desktop
2. Open terminal and run the commands above

---

### 🥧 **Raspberry Pi**

**Method 1: HDMI + Keyboard**
1. Connect HDMI cable and USB keyboard
2. Boot up the Pi
3. Open terminal and run:
```bash
sudo systemctl enable ssh
sudo systemctl start ssh
```

**Method 2: Desktop Interface**
1. Connect HDMI and keyboard
2. Go to: **Menu → Preferences → Raspberry Pi Configuration**
3. Click **Interfaces** tab
4. Enable **SSH**
5. Click **OK** and reboot

**Method 3: SD Card Method (if Pi is powered off)**
1. Remove SD card from Pi
2. Insert into Windows PC
3. Create empty file named `ssh` (no extension) in the root of the SD card
4. Insert SD card back into Pi and boot

---

### 🌐 **Router or Network Device**

If `192.168.0.1` is your router:
1. Open web browser: **http://192.168.0.1**
2. Login with admin credentials  
3. Look for:
   - **Administration → SSH**
   - **Services → SSH**
   - **Advanced → Remote Management**
4. Enable SSH/Remote CLI access
5. Set username/password for SSH

---

### 💻 **Windows Server**

**Enable OpenSSH Server:**
1. Connect physically or via RDP
2. Open **Settings → Apps & Features → Optional Features**
3. Click **Add a feature**  
4. Find and install **OpenSSH Server**
5. Open **Services** and start **OpenSSH SSH Server**
6. Configure Windows Firewall to allow SSH (port 22)

---

## Step 3: Test SSH Connection

After enabling SSH, test from your Windows machine:

```powershell
# Test if SSH port is now open
Test-NetConnection -ComputerName 192.168.0.1 -Port 22

# Try SSH connection
ssh rds@192.168.0.1
# or try with default usernames:
ssh admin@192.168.0.1
ssh pi@192.168.0.1      # if Raspberry Pi
ssh ubuntu@192.168.0.1  # if Ubuntu server
```

---

## Step 4: Deploy ArmGuard Once SSH Works

Once SSH is working, use these deployment scripts:

**Quick Deployment:**
```bash
# Copy this project to the target
scp -r . rds@192.168.0.1:~/armguard/

# SSH to the server and deploy
ssh rds@192.168.0.1
cd ~/armguard/deployment
sudo ./deploy-master.sh redis-setup    # Install Redis for WebSockets  
sudo ./deploy-master.sh production     # Full ArmGuard deployment
```

**Or use the automated deployment:**
```bash
# From Windows, run:
cd deployment
chmod +x remote-deployment-helper.sh
./remote-deployment-helper.sh
```

---

## Troubleshooting Common Issues

### "Permission denied (publickey)"
If you get authentication errors:
```bash
# Try password authentication
ssh -o PreferredAuthentications=password rds@192.168.0.1

# Or try common default usernames
ssh admin@192.168.0.1
ssh pi@192.168.0.1  
ssh ubuntu@192.168.0.1
ssh root@192.168.0.1
```

### Still Can't Connect?
1. **Check firewall on target system:**
   ```bash
   sudo ufw status          # Ubuntu
   sudo firewall-cmd --list-all  # RHEL/CentOS
   ```

2. **Verify SSH is listening:**
   ```bash
   sudo netstat -tlnp | grep :22
   # or
   sudo ss -tlnp | grep :22
   ```

3. **Check SSH configuration:**
   ```bash
   sudo nano /etc/ssh/sshd_config
   # Ensure: Port 22, PermitRootLogin yes (temporarily)
   sudo systemctl restart ssh
   ```

---

## Alternative Access Methods

If SSH still doesn't work:

### 1. **Web-based Terminal** 
Some systems have web-based terminals:
- **Cockpit**: http://192.168.0.1:9090
- **Webmin**: http://192.168.0.1:10000  
- **Router CLI**: Check router documentation

### 2. **Serial Console** 
If you have a USB-to-Serial adapter:
- Connect to GPIO/Serial pins (Raspberry Pi)
- Use PuTTY with serial connection

### 3. **Network Boot/PXE**
For servers that support it:
- Boot from network installer
- Enable SSH during installation

---

## Summary

**Your Action Plan:**
1. 🔍 **Identify system type** - check web interface at http://192.168.0.1
2. 🔌 **Get physical access** - connect keyboard/monitor if needed
3. ⚙️ **Enable SSH** - follow instructions for your system type  
4. 🧪 **Test connection** - `ssh rds@192.168.0.1` 
5. 🚀 **Deploy ArmGuard** - use deployment scripts with Redis optimization

**Need help?** Tell me:
- What type of system is at `192.168.0.1`?  
- Can you connect physically (keyboard/monitor)?
- Does http://192.168.0.1 show a web interface?