# Gunicorn Permission Issue - Root Cause Analysis

## Issue Summary

**Error:** `gunicorn-armguard.service: Changing to the requested working directory failed: Permission denied`

**Exit Code:** 200/CHDIR (Cannot change directory)

**Restart Counter:** 65+ attempts (continuous failure loop)

## Root Cause Analysis

### 1. **Primary Issue: Directory Access Permissions**

The Gunicorn service is configured to:
- Run as user: `www-data`
- Run as group: `www-data`
- Working directory: `/var/www/armguard`

However, the `www-data` user cannot access `/var/www/armguard` because:

1. **The directory likely doesn't exist in the expected location**
   - Project was deployed from `/home/rds/ARMGUARD_RDS_v.2/armguard`
   - Service expects files at `/var/www/armguard`
   - No automatic copy/sync mechanism between these locations

2. **Wrong ownership on the directory**
   - Directory (if it exists) is owned by `rds:rds`
   - Service runs as `www-data:www-data`
   - www-data cannot read/execute the directory

3. **Parent directory (`/var/www`) permissions**
   - Even if `/var/www/armguard` has correct permissions
   - Must traverse through `/var/www` first
   - Parent directory must have execute (x) permission for www-data

### 2. **Deployment Script Gaps**

#### Found in `deploy-armguard.sh` (Lines 354-365):
```bash
setup_project_directory() {
    # Verify project directory exists and contains Django files
    if [ ! -d "$PROJECT_DIR" ]; then
        echo -e "${RED}ERROR: Project directory does not exist: ${PROJECT_DIR}${NC}"
        exit 1
    fi
```

**Issue:** Script assumes project directory already exists. It does NOT create or copy files to `/var/www/armguard`.

#### Found in `install-gunicorn-service.sh` (Lines 195-199):
```bash
echo -e "${YELLOW}Setting permissions...${NC}"
chown -R ${RUN_USER}:${RUN_GROUP} ${PROJECT_DIR}
chmod 600 ${PROJECT_DIR}/.env 2>/dev/null || echo -e "${YELLOW}  Warning: .env file not found${NC}"
```

**Issue:** Attempts to fix permissions, but:
- Only runs if service installation completes
- Doesn't verify www-data can actually access the directory
- Doesn't fix parent directory permissions

### 3. **Systemd Service Configuration Issues**

From `gunicorn-armguard.service`:
```ini
[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/armguard

# Security settings
ProtectSystem=strict
ReadWritePaths=/var/www/armguard /var/log/armguard /run
```

**Issues:**
- `ProtectSystem=strict` creates a read-only filesystem except for specified paths
- Can cause additional permission issues
- `ReadWritePaths` doesn't automatically grant access - base permissions must be correct first

### 4. **Missing Deployment Step**

The deployment workflow has a gap:

```
Current Flow:
1. User has project at: /home/rds/ARMGUARD_RDS_v.2/armguard
2. deploy-armguard.sh expects: /var/www/armguard
3. ❌ No automated copy/sync step
4. install-gunicorn-service.sh runs
5. Service fails - directory doesn't exist or has wrong permissions
```

## Detailed Technical Analysis

### Permission Requirements for systemd Directory Access

For `www-data` to successfully `cd /var/www/armguard`, the following must be true:

1. **Root directory `/`:**
   - Must have execute permission for others (typical: 755)
   - ✓ Almost always correct by default

2. **Parent directory `/var`:**
   - Must have execute permission for others (typical: 755)
   - ✓ Almost always correct by default

3. **Parent directory `/var/www`:**
   - Must have execute permission for others (minimum: 755)
   - ❌ **LIKELY ISSUE:** May not exist or may have restrictive permissions
   - ❌ May be owned incorrectly

4. **Target directory `/var/www/armguard`:**
   - Must have read + execute permissions for www-data
   - Either owned by www-data:www-data (755 or 700)
   - Or world-readable (755) with any owner
   - ❌ **PRIMARY ISSUE:** Doesn't exist or owned by wrong user

### What Happens at Service Start

1. Systemd reads service file
2. Sets user context to `www-data`
3. Attempts: `cd /var/www/armguard`
4. Kernel checks permissions:
   - Can www-data traverse `/var/www`? → Likely NO
   - Can www-data access `/var/www/armguard`? → Likely NO
5. Returns error: EACCES (Permission denied)
6. Systemd logs: "Changing to the requested working directory failed"
7. Exit code: 200 (CHDIR failure)
8. Systemd restarts service (Restart=always)
9. Infinite loop

## Solutions

### Solution 1: Immediate Fix (Manual)

```bash
# Stop the failing service
sudo systemctl stop gunicorn-armguard

# Create and set up the directory
sudo mkdir -p /var/www/armguard

# Copy project files (from wherever they currently are)
sudo rsync -av \
  --exclude='.git' \
  --exclude='*.pyc' \
  --exclude='__pycache__' \
  --exclude='*.sqlite3' \
  --exclude='.venv' \
  /home/rds/ARMGUARD_RDS_v.2/armguard/ \
  /var/www/armguard/

# Fix parent directory permissions
sudo chmod 755 /var/www
sudo chown root:root /var/www

# Fix project directory ownership
sudo chown -R www-data:www-data /var/www/armguard

# Fix directory permissions (755 = rwxr-xr-x)
sudo find /var/www/armguard -type d -exec chmod 755 {} \;

# Fix file permissions (644 = rw-r--r--)
sudo find /var/www/armguard -type f -exec chmod 644 {} \;

# Make executables executable
sudo chmod +x /var/www/armguard/.venv/bin/* 2>/dev/null || true

# Secure sensitive files
sudo chmod 600 /var/www/armguard/.env
sudo chmod 664 /var/www/armguard/db.sqlite3

# Create log directories
sudo mkdir -p /var/log/armguard
sudo chown -R www-data:www-data /var/log/armguard

# Restart service
sudo systemctl daemon-reload
sudo systemctl start gunicorn-armguard
sudo systemctl status gunicorn-armguard
```

### Solution 2: Automated Fix Script

Use the provided `fix-gunicorn-permissions.sh` script:

```bash
cd ~/ARMGUARD_RDS_v.2/armguard/deployment_A/methods/production
chmod +x fix-gunicorn-permissions.sh
sudo ./fix-gunicorn-permissions.sh
```

This script will:
1. Analyze the current setup
2. Copy project files if needed
3. Fix all permission issues systematically
4. Update service configuration if needed
5. Test permissions before starting service
6. Start service and verify it's working

### Solution 3: Update Deployment Scripts

**Required changes to `deploy-armguard.sh`:**

```bash
# Add this function before setup_project_directory()
copy_project_to_deployment() {
    local source_dir="$1"
    local target_dir="$2"
    
    echo -e "${YELLOW}Copying project files...${NC}"
    
    # Create parent directory
    mkdir -p "$(dirname "$target_dir")"
    chmod 755 "$(dirname "$target_dir")"
    
    # Create target directory
    mkdir -p "$target_dir"
    
    # Copy files
    rsync -av \
        --exclude='.git' \
        --exclude='*.pyc' \
        --exclude='__pycache__' \
        --exclude='*.sqlite3' \
        --exclude='.venv' \
        --exclude='venv' \
        --exclude='node_modules' \
        "$source_dir/" "$target_dir/"
    
    echo -e "${GREEN}✓ Project files copied${NC}"
}

# Update setup_project_directory():
setup_project_directory() {
    echo ""
    echo -e "${BLUE}Step 2: Setting Up Project Directory${NC}"
    
    # Detect current project location
    CURRENT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)
    
    if [ ! -d "$PROJECT_DIR" ]; then
        echo -e "${YELLOW}Project directory does not exist: ${PROJECT_DIR}${NC}"
        
        if [ -d "$CURRENT_DIR/manage.py" ]; then
            read -p "Copy from $CURRENT_DIR? (yes/no): " COPY_CONFIRM
            if [[ "$COPY_CONFIRM" =~ ^[Yy] ]]; then
                copy_project_to_deployment "$CURRENT_DIR" "$PROJECT_DIR"
            else
                echo -e "${RED}ERROR: Cannot proceed without project files${NC}"
                exit 1
            fi
        else
            echo -e "${RED}ERROR: Cannot find project source${NC}"
            exit 1
        fi
    fi
    
    # Verify and fix permissions
    chmod 755 "$(dirname "$PROJECT_DIR")"
    chown -R $RUN_USER:$RUN_GROUP "$PROJECT_DIR"
    
    cd "$PROJECT_DIR"
    
    if [ ! -f "manage.py" ]; then
        echo -e "${RED}ERROR: manage.py not found${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✓ Project directory ready${NC}"
}
```

## Recommended Deployment Flow

### Option A: Deploy to /var/www/armguard (Production Standard)

**Advantages:**
- Standard Linux production deployment location
- Clear separation from development files
- Easier to manage multiple deployments

**Process:**
1. Copy project files to `/var/www/armguard`
2. Set ownership to `www-data:www-data`
3. Create venv at `/var/www/armguard/.venv`
4. Install dependencies
5. Configure and start services

### Option B: Deploy from /home/rds (Alternative)

**Advantages:**
- Files stay in user directory
- Easier to update with git pull
- No need to copy files

**Changes Required:**
1. Update gunicorn-armguard.service:
   ```ini
   User=rds
   Group=rds
   WorkingDirectory=/home/rds/ARMGUARD_RDS_v.2/armguard
   ```
2. Update nginx configuration to match
3. Update all log paths
4. Update `config.sh` defaults

## Verification Checklist

After applying any fix, verify:

- [ ] `/var/www` exists and has 755 permissions
- [ ] `/var/www/armguard` exists and has correct ownership
- [ ] www-data can read: `sudo -u www-data test -r /var/www/armguard/manage.py`
- [ ] www-data can execute directory: `sudo -u www-data test -x /var/www/armguard`
- [ ] Virtual environment exists: `/var/www/armguard/.venv/bin/gunicorn`
- [ ] Service file is correct: `/etc/systemd/system/gunicorn-armguard.service`
- [ ] Service starts: `sudo systemctl start gunicorn-armguard`
- [ ] Service is active: `sudo systemctl is-active gunicorn-armguard`
- [ ] Socket created: `ls -l /run/gunicorn-armguard.sock`
- [ ] No errors in journal: `sudo journalctl -u gunicorn-armguard -n 20`

## Prevention for Future Deployments

1. **Add pre-flight checks** in deployment scripts:
   ```bash
   verify_directory_access() {
       local user=$1
       local directory=$2
       if ! sudo -u $user test -x "$directory"; then
           echo "ERROR: $user cannot access $directory"
           return 1
       fi
   }
   ```

2. **Add permission verification** before service start:
   ```bash
   verify_service_permissions() {
       echo "Testing service permissions..."
       sudo -u $RUN_USER test -r "$PROJECT_DIR/manage.py" || return 1
       sudo -u $RUN_USER test -x "$PROJECT_DIR/.venv/bin/gunicorn" || return 1
       return 0
   }
   ```

3. **Update service file** to provide better error messages:
   ```ini
   [Service]
   # Add this to get better debugging
   StandardOutput=journal
   StandardError=journal
   ```

4. **Add health check** after deployment:
   ```bash
   check_service_health() {
       sleep 3
       if systemctl is-active --quiet gunicorn-armguard; then
           echo "✓ Service is running"
       else
           echo "✗ Service failed"
           journalctl -u gunicorn-armguard -n 50
           exit 1
       fi
   }
   ```

## Additional Notes

### Security Considerations

- **Never use 777 permissions** - this is a security risk
- **Keep .env at 600** - contains sensitive information
- **Database should be 664** - allows group write access
- **Directories should be 755** - allows traverse but not write
- **Regular files should be 644** - readable but not writable by others

### Troubleshooting Commands

```bash
# Check what user a service runs as
sudo systemctl show -p User,Group gunicorn-armguard

# Test directory access as specific user
sudo -u www-data ls -la /var/www/armguard

# Check directory permissions recursively
namei -l /var/www/armguard

# Find files not owned by www-data
find /var/www/armguard ! -user www-data ! -group www-data

# Check service dependencies
systemctl list-dependencies gunicorn-armguard

# View full service output
journalctl -u gunicorn-armguard --no-pager -o cat
```

## References

- systemd service file documentation
- Linux file permissions (chmod/chown)
- Gunicorn deployment guide
- Django production deployment best practices
