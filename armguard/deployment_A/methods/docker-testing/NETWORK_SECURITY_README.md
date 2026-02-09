# ArmGuard Docker Testing Environment - Network Security Implementation
# Updated for LAN/WAN Military-Grade Security Architecture

## Overview

This Docker testing environment now includes **military-grade network security** with separated LAN and WAN access:

- **LAN Access (Port 8443)**: Full access to transactions, registration, and admin functions
- **WAN Access (Port 443)**: Read-only access for status checking only

## Quick Start

```bash
# 1. Copy network security environment template
cp .env.network-security .env

# 2. Edit configuration for your environment
nano .env

# 3. Start the complete testing stack
docker-compose --profile testing --profile monitoring up -d

# 4. Generate SSL certificates (if needed)
./nginx/ssl/generate-certs.sh

# 5. Access the application
# LAN: https://localhost:8443 (Full access)
# WAN: https://localhost:443 (Status checking only)
```

## Network Security Features

### 🔒 **Dual-Port Architecture**
- **Port 8443 (LAN)**: Sensitive operations
  - ✅ User registration
  - ✅ Transaction processing  
  - ✅ QR code scanning
  - ✅ Admin panel access
  - ✅ Full CRUD operations

- **Port 443 (WAN)**: Status operations only
  - ✅ Personnel status checking
  - ✅ Inventory viewing
  - ✅ Search functionality
  - ❌ Registration blocked
  - ❌ Transactions blocked
  - ❌ Admin access blocked

### 🛡️ **Enhanced Security Headers**
- Strict Content Security Policy
- HSTS enforcement
- Frame protection
- XSS protection
- Network access identification headers

### ⚡ **Rate Limiting**
- Login attempts: 5 per minute
- API calls: 30 per second (LAN), 60 per minute (WAN)
- General requests: Differentiated by network type

## Service Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   LAN Clients   │───▶│  Nginx (8443)   │───▶│ Django App      │
│  Full Access    │    │  Full Routing    │    │ All Operations  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                               │
┌─────────────────┐    ┌──────────────────┐            │
│   WAN Clients   │───▶│  Nginx (443)    │────────────┘
│  Read Only      │    │ Restricted Proxy │
└─────────────────┘    └──────────────────┘
```

## Environment Variables

Key network security variables in `.env`:

```bash
# Network Security
NETWORK_SECURITY_ENABLED=true
LAN_PORT=8443
WAN_PORT=443
FORCE_NETWORK_SECURITY=true

# CSRF Origins (both ports)
CSRF_TRUSTED_ORIGINS=https://localhost,https://localhost:8443,https://armguard.local,https://armguard.local:8443
```

## Testing Network Security

### Test LAN Access (Port 8443)
```bash
# Should work - Registration
curl -k https://localhost:8443/register/

# Should work - Transactions
curl -k https://localhost:8443/transactions/

# Should work - Admin
curl -k https://localhost:8443/admin/
```

### Test WAN Restrictions (Port 443)
```bash
# Should be blocked - Registration
curl -k https://localhost:443/register/
# Expected: 403 Forbidden

# Should be blocked - Transactions  
curl -k https://localhost:443/transactions/
# Expected: 403 Forbidden

# Should work - Status checking
curl -k https://localhost:443/personnel/
```

## Monitoring Stack

Access monitoring tools (when using `--profile monitoring`):

- **Grafana**: http://localhost:3000 (admin/armguard_grafana)
- **Prometheus**: http://localhost:9090
- **AlertManager**: http://localhost:9093

## Security Testing

The environment includes comprehensive security testing:

```bash
# Run security scan with OWASP ZAP
docker-compose --profile testing exec zap zap-baseline.py -t https://armguard-app:8443

# Run load testing
docker-compose --profile testing exec locust locust -f /tests/locustfile.py --host=https://armguard-app:8443
```

## Deployment Profiles

- **Basic**: `docker-compose up -d` (core services only)
- **Testing**: `docker-compose --profile testing up -d` (includes testing tools)
- **Full Stack**: `docker-compose --profile testing --profile monitoring up -d` (complete stack)

## Network Security Validation

The nginx configuration automatically:

1. **Routes LAN traffic** (port 8443) with full access
2. **Restricts WAN traffic** (port 443) to read-only operations
3. **Blocks sensitive endpoints** on WAN
4. **Adds network identification headers** for Django middleware
5. **Enforces rate limits** based on network type

## Troubleshooting

### Common Issues

1. **SSL Certificate Errors**
   ```bash
   ./nginx/ssl/generate-certs.sh
   docker-compose restart nginx
   ```

2. **Port Conflicts**
   - Check if ports 443/8443 are in use
   - Modify docker-compose.yml ports if needed

3. **Network Access Issues**
   - Verify NETWORK_SECURITY_ENABLED=true in .env
   - Check Django middleware configuration
   - Review nginx access logs

### Logs Access

```bash
# Application logs
docker-compose logs armguard-app

# Nginx access/error logs
docker-compose logs nginx

# Database logs
docker-compose logs armguard-db
```

## Production Readiness

This docker testing environment is designed for:

- ✅ **Development testing**
- ✅ **Security validation** 
- ✅ **Load testing**
- ✅ **CI/CD integration**
- ❌ **Direct production use** (use production deployment method instead)

For production deployment, use the dedicated [production deployment method](../production/README.md) which includes additional security hardening and optimization.