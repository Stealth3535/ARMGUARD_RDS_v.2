# ArmGuard Deployment Architecture Fixes v2.1

## Overview

This document summarizes the synchronization fixes and architectural improvements made to the deployment system.

---

## 🔧 Issues Fixed

### 1. Socket Path Inconsistency ✅

**Problem:** Different scripts used different socket paths:
- `install-nginx.sh` used `/var/www/armguard/gunicorn.sock`
- Others used `/run/gunicorn-armguard.sock`

**Solution:** Standardized all scripts to use `/run/gunicorn-armguard.sock`

**Files Updated:**
- `install-nginx.sh`
- `install-mkcert-ssl.sh`

---

### 2. Service Type Mismatch ✅

**Problem:** `gunicorn-armguard.service` used `Type=notify`, but Gunicorn doesn't support systemd notify protocol without special configuration.

**Solution:** Changed to `Type=exec` and added:
- `ExecReload` for graceful reloads
- `ProtectSystem=strict` for security
- `ReadWritePaths` for proper access
- Optional `EnvironmentFile` with `-` prefix

**Files Updated:**
- `gunicorn-armguard.service`

---

### 3. Centralized Configuration Not Used ✅

**Problem:** Scripts defined their own variables instead of sourcing `config.sh`.

**Solution:** Added `config.sh` sourcing to all scripts:

```bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/config.sh" ]; then
    source "$SCRIPT_DIR/config.sh"
fi
```

**Files Updated:**
- `health-check.sh`
- `rollback.sh`
- `update-armguard.sh`
- `pre-check.sh`
- `network_setup/setup-lan-network.sh`
- `network_setup/setup-wan-network.sh`
- `network_setup/configure-firewall.sh`
- `network_setup/verify-network.sh`

---

### 4. Media Directory Inconsistency ✅

**Problem:** 
- `settings.py` used `core/media/`
- `settings_production.py` used `media/`
- Nginx configs used `core/media/`

**Solution:** Updated `settings_production.py` to match:
```python
MEDIA_ROOT = BASE_DIR / 'core' / 'media'
```

**Files Updated:**
- `core/settings_production.py`

---

### 5. Network Setup Scripts Missing Config Integration ✅

**Problem:** Network setup scripts used hardcoded values instead of configuration.

**Solution:** Added config.sh sourcing with fallback defaults:

```bash
DEPLOYMENT_DIR="$(dirname "$SCRIPT_DIR")"
if [ -f "$DEPLOYMENT_DIR/config.sh" ]; then
    source "$DEPLOYMENT_DIR/config.sh"
fi

# Configuration with defaults
LAN_INTERFACE="${LAN_INTERFACE:-eth1}"
SERVER_LAN_IP="${SERVER_LAN_IP:-192.168.10.1}"
```

**Files Updated:**
- All files in `network_setup/`

---

### 6. Missing Network Configuration Variables ✅

**Problem:** `config.sh` didn't include hybrid network settings.

**Solution:** Added network variables:

```bash
export LAN_INTERFACE="${ARMGUARD_LAN_INTERFACE:-eth1}"
export WAN_INTERFACE="${ARMGUARD_WAN_INTERFACE:-eth0}"
export LAN_SUBNET="${ARMGUARD_LAN_SUBNET:-192.168.10.0/24}"
export SERVER_LAN_IP="${ARMGUARD_LAN_IP:-192.168.10.1}"
export ARMORY_PC_IP="${ARMGUARD_ARMORY_IP:-192.168.10.2}"
```

**Files Updated:**
- `config.sh`

---

## 🆕 New Files Created

### `master-deploy.sh` - Orchestrated Deployment

A new master deployment script that:
- Orchestrates all deployment phases in correct order
- Sources centralized configuration
- Supports different network types (lan/wan/hybrid)
- Includes comprehensive error handling
- Provides deployment summary

**Usage:**
```bash
sudo bash deployment/master-deploy.sh --network-type lan
sudo bash deployment/master-deploy.sh --network-type hybrid
```

**10 Deployment Phases:**
1. Environment Detection & Pre-checks
2. System Dependencies Installation
3. Python Environment Setup
4. Database Setup & Migrations
5. Gunicorn Service Installation
6. Nginx Configuration
7. SSL Certificate Setup
8. Firewall Configuration
9. Log Rotation Setup
10. Health Check & Verification

---

## 📊 Architecture After Fixes

```
config.sh (Central Configuration)
    ↓
    ├── master-deploy.sh (Orchestrator)
    │       ↓
    │       ├── pre-check.sh
    │       ├── detect-environment.sh
    │       ├── install-gunicorn-service.sh (uses config)
    │       ├── install-nginx-enhanced.sh (uses config)
    │       ├── network_setup/setup-lan-network.sh (uses config)
    │       ├── network_setup/configure-firewall.sh (uses config)
    │       ├── setup-logrotate.sh
    │       └── health-check.sh (uses config)
    │
    ├── update-armguard.sh (uses config)
    │       ↓
    │       ├── health-check.sh
    │       └── rollback.sh (uses config)
    │
    └── All scripts share:
        - Socket path: /run/gunicorn-armguard.sock
        - Service name: gunicorn-armguard
        - Project dir: /var/www/armguard
        - Media dir: /var/www/armguard/core/media
```

---

## ✅ Verification Checklist

- [x] All socket paths standardized to `/run/gunicorn-armguard.sock`
- [x] Service type changed to `exec` (compatible with Gunicorn)
- [x] All scripts source `config.sh`
- [x] Media directory consistent across settings and Nginx
- [x] Network variables added to config.sh
- [x] New master deployment script created
- [x] README updated with v2.1 features

---

## 🚀 Deployment Flow (Recommended)

```bash
# One-command deployment
sudo bash deployment/master-deploy.sh --network-type lan

# Or manual step-by-step
sudo bash deployment/pre-check.sh
sudo bash deployment/deploy-armguard.sh
sudo bash deployment/install-nginx-enhanced.sh
sudo bash deployment/install-mkcert-ssl.sh
sudo bash deployment/health-check.sh
```

---

## 📝 Configuration Override

Users can customize deployment via environment variables:

```bash
# Override network settings
export LAN_INTERFACE="enp0s8"
export SERVER_LAN_IP="10.0.0.1"
export ARMGUARD_WORKERS=4

# Run deployment
sudo bash deployment/master-deploy.sh --network-type lan
```

Or create `config.local.sh`:

```bash
# /var/www/armguard/deployment/config.local.sh
export ARMGUARD_WORKERS=4
export ARMGUARD_DOMAIN="myarmguard.local"
```

---

**Version:** 2.1  
**Date:** January 28, 2026  
**Status:** Production Ready
