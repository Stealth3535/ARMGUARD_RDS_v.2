# 🚀 ArmGuard Deployment Quick Reference

**Version:** 3.0.0 | **Status:** ✅ Production Ready | **Last Updated:** February 1, 2026

## ⚡ One-Command Deployment

```bash
cd armguard/deployment

# Choose your deployment method:
./deploy-master.sh vm-test      # VMware VM testing
./deploy-master.sh basic-setup  # Simple server
./deploy-master.sh production   # Enterprise deployment
./deploy-master.sh docker-test  # Container testing
```

## 🎯 Quick Method Selection

| Method | Use Case | Time | Complexity | Features |
|--------|----------|------|------------|----------|
| `vm-test` | Development/Testing | 15 min | ⭐ Easy | Basic setup, shared folders |
| `basic-setup` | Simple production | 30 min | ⭐⭐ Medium | Essential services only |
| `production` | Enterprise | 60 min | ⭐⭐⭐ Advanced | Full features, monitoring |
| `docker-test` | CI/CD Testing | 45 min | ⭐⭐⭐ Advanced | Complete test suite |

## 🔍 Status & Information

```bash
# System status
./deploy-master.sh status

# Available methods
./deploy-master.sh list

# Current configuration
./deploy-master.sh --config

# Help and usage
./deploy-master.sh help
```

## 🛠️ Common Management Tasks

### Service Management
```bash
# Check service status
sudo systemctl status armguard

# Restart application
sudo systemctl restart armguard

# View logs
sudo journalctl -u armguard -f
```

### Application Updates
```bash
# Production updates
cd methods/production
sudo ./update-armguard.sh

# Health check after update
./health-check.sh
```

### Backup & Recovery
```bash
# Manual backup
cd methods/production
sudo ./secure-backup.sh --manual

# Restore from backup
sudo ./rollback.sh --backup-date 2026-02-01
```

## 🏗️ Environment Details

### VM Test Environment
- **Path**: `/mnt/hgfs/Armguard/armguard`
- **Access**: `http://{VM_IP}/`
- **Admin**: `admin/admin123`
- **Database**: PostgreSQL test instance

### Basic Setup
- **Path**: `/var/www/armguard`
- **Access**: Configured during setup
- **Database**: SQLite or PostgreSQL
- **Features**: Essential services only

### Production Deployment
- **Path**: `/opt/armguard`
- **Access**: `https://{domain}`
- **Database**: PostgreSQL with pooling
- **Features**: Full enterprise stack

### Docker Testing
- **Path**: Container volumes
- **Access**: `http://localhost`
- **Features**: Complete testing + monitoring
- **Dashboards**: Grafana, Prometheus

## 🔧 Troubleshooting

### Quick Fixes
```bash
# Fix permissions
sudo chown -R armguard:armguard /opt/armguard

# Restart all services
sudo systemctl restart nginx postgresql redis-server armguard

# Check configuration
./deploy-master.sh --config

# Test deployment
./deploy-master.sh vm-test --dry-run
```

### Log Locations
- **Application**: `/var/log/armguard/`
- **System**: `journalctl -u armguard`
- **Nginx**: `/var/log/nginx/`
- **PostgreSQL**: `/var/log/postgresql/`

## 📚 Documentation Links

- **Main Guide**: [README.md](README.md)
- **VM Setup**: [methods/vmware-setup/README.md](methods/vmware-setup/README.md)
- **Basic Setup**: [methods/basic-setup/README.md](methods/basic-setup/README.md)
- **Production**: [methods/production/README.md](methods/production/README.md)
- **Docker Testing**: [methods/docker-testing/README.md](methods/docker-testing/README.md)
- **Validation Report**: [VALIDATION_REPORT.md](VALIDATION_REPORT.md)

---

**Need Help?** Run `./deploy-master.sh help` or check method-specific documentation!