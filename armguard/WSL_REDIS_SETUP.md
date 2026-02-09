# WSL + Redis Setup Instructions for ArmGuard

## Quick WSL Installation

### Option A: Current Prompt (Easy)
Your terminal is showing WSL installation prompt:
- Press **ANY KEY** → Automatic WSL installation
- **Restart computer** when prompted  
- Continue to Redis installation

### Option B: Manual Administrative Install
1. **Right-click PowerShell** → "Run as Administrator"  
2. Run: `wsl --install`
3. **Restart computer**
4. Continue to Redis installation

## After WSL Installation

### Step 1: Install Redis in WSL
```bash
# Update package lists
wsl sudo apt update

# Install Redis server  
wsl sudo apt install -y redis-server

# Start Redis service
wsl sudo service redis-server start

# Verify Redis is running
wsl redis-cli ping
# Should respond: PONG
```

### Step 2: Test Django Connection
```bash
# Back in Windows PowerShell
cd "c:\Users\9533RDS\Desktop\ARMGUARD_RDS_v.2\armguard"
python manage.py runserver
```

You should see:
```
✅ Using Redis for WebSocket channel layer
```

## Redis Management Commands

### Start Redis (if stopped):
```bash
wsl sudo service redis-server start
```

### Stop Redis:
```bash  
wsl sudo service redis-server stop
```

### Check Redis status:
```bash
wsl sudo service redis-server status
```

### Auto-start Redis on boot:
```bash
wsl sudo systemctl enable redis-server
```

## Troubleshooting

### If Redis connection fails:
1. Check if WSL is running: `wsl --list --running`
2. Start WSL: `wsl`  
3. Check Redis: `wsl sudo service redis-server status`
4. Restart Redis: `wsl sudo service redis-server restart`

### If WSL is slow:
- Increase WSL memory in `.wslconfig` file in `%USERPROFILE%`
- Restart WSL: `wsl --shutdown` then `wsl`

## Benefits After Setup
- ✅ Optimal WebSocket performance
- ✅ Handle more concurrent users  
- ✅ Better real-time notifications
- ✅ Professional Redis development environment
- ✅ Persistent data across restarts