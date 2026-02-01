# Enterprise Production Deployment

Complete production deployment with enterprise features, monitoring, security, and automation.

## Overview

- **Target**: Production servers (Ubuntu/Debian/CentOS)
- **Purpose**: Full-scale production deployment
- **Features**: All enterprise features enabled
- **Database**: PostgreSQL with connection pooling
- **Path**: `/opt/armguard`
- **Security**: Full security hardening with SSL/TLS

## Prerequisites

### System Requirements
- **OS**: Ubuntu 20.04+, Debian 11+, CentOS 8+, or RHEL 8+
- **RAM**: 4GB minimum (8GB recommended)
- **Storage**: 50GB free space (100GB recommended)
- **Network**: Static IP, domain name, firewall access
- **CPU**: 2 cores minimum (4+ recommended)

### Infrastructure Requirements
- **Domain name**: For SSL certificate generation
- **Email address**: For ACME/Let's Encrypt certificates
- **Firewall access**: Ports 80, 443, 22
- **Backup storage**: External storage for encrypted backups
- **Monitoring**: Optional Prometheus/Grafana setup

### Access Requirements
- Root/sudo access on target server
- SSH access to server
- DNS control for domain configuration

## Quick Start

### 1. Deploy from Master Script
```bash
cd armguard/deployment
./deploy-master.sh production
```

### 2. Direct Production Deployment
```bash
cd armguard/deployment/methods/production
chmod +x master-deploy.sh
sudo ./master-deploy.sh
```

### 3. Check Deployment Status
```bash
./deploy-master.sh status
```

## Architecture

### Directory Structure
```
/opt/armguard/
├── armguard/                    # Django application
├── venv/                        # Python virtual environment
├── logs/                        # Application logs
├── backups/                     # Local backup storage
├── ssl/                         # SSL certificates
└── config/                      # Configuration files

/var/www/armguard/
├── static/                      # Static files (Nginx)
├── media/                       # User uploads
└── logs/                        # Web server logs

/var/log/armguard/               # System logs
/var/backups/armguard/           # System backups
/etc/systemd/system/armguard.service  # Systemd service
```

### Network Architecture
- **Nginx**: Reverse proxy with SSL termination
- **Gunicorn**: WSGI application server
- **PostgreSQL**: Primary database
- **Redis**: Caching and session storage
- **Certbot**: SSL certificate management

## Enterprise Features

### Security Features
- ✅ **SSL/TLS encryption** with automated certificate renewal
- ✅ **Security headers** (HSTS, CSP, X-Frame-Options)
- ✅ **Rate limiting** and DDoS protection
- ✅ **Firewall configuration** with fail2ban
- ✅ **Secrets management** (Vault/AWS/Azure integration)
- ✅ **Encrypted backups** with rotation
- ✅ **Security scanning** and vulnerability checks

### Monitoring & Observability
- ✅ **Prometheus** metrics collection
- ✅ **Grafana** dashboards and visualization
- ✅ **Alertmanager** notification routing
- ✅ **Log aggregation** with structured logging
- ✅ **Health checks** and uptime monitoring
- ✅ **Performance monitoring** with APM

### Backup & Recovery
- ✅ **Automated backups** with configurable schedule
- ✅ **Encrypted backup storage** (local and remote)
- ✅ **Point-in-time recovery**
- ✅ **Database backup verification**
- ✅ **Rollback capabilities**
- ✅ **Disaster recovery procedures**

### High Availability
- ✅ **Load balancing** support
- ✅ **Database connection pooling**
- ✅ **Graceful service restarts**
- ✅ **Zero-downtime deployments**
- ✅ **Service health monitoring**
- ✅ **Auto-scaling preparation**

## Deployment Process

### Phase 1: System Preparation
1. **Environment detection** and validation
2. **System package updates**
3. **Security hardening** and user creation
4. **Firewall configuration**
5. **Directory structure** creation

### Phase 2: Database Setup
1. **PostgreSQL installation** and configuration
2. **Database creation** with proper permissions
3. **Connection pooling** setup
4. **Performance tuning**
5. **Backup configuration**

### Phase 3: Application Deployment
1. **Python environment** setup
2. **Django application** installation
3. **Database migrations**
4. **Static file collection**
5. **Superuser creation**

### Phase 4: Web Server Configuration
1. **Nginx installation** and SSL setup
2. **Gunicorn service** configuration
3. **SSL certificate** generation
4. **Security headers** configuration
5. **Rate limiting** setup

### Phase 5: Monitoring Setup
1. **Log rotation** configuration
2. **Health checks** implementation
3. **Monitoring stack** deployment
4. **Alert configuration**
5. **Performance baseline** establishment

### Phase 6: Security Hardening
1. **Secrets management** setup
2. **Backup encryption** configuration
3. **Network security** rules
4. **Access control** implementation
5. **Security scanning** setup

## Configuration

### Environment Variables
```bash
# Production settings
ENVIRONMENT=production
DEBUG=false
PROJECT_DIR=/opt/armguard/armguard
STATIC_DIR=/var/www/armguard/static
MEDIA_DIR=/var/www/armguard/media

# Database
DB_ENGINE=postgresql
DB_NAME=armguard_prod
DB_USER=armguard
DB_HOST=localhost
DB_PORT=5432

# Security
SSL_ENABLED=true
DOMAIN=your-domain.com
SECRET_KEY=auto-generated

# Monitoring
PROMETHEUS_ENABLED=true
GRAFANA_ENABLED=true
LOG_LEVEL=INFO

# Backup
BACKUP_ENABLED=true
BACKUP_ENCRYPTION=true
BACKUP_SCHEDULE="0 2 * * *"  # Daily at 2 AM
```

### Network Configuration

#### LAN Deployment
```bash
# Deploy with mkcert for local SSL
./master-deploy.sh --network-type lan
```

#### WAN Deployment
```bash
# Deploy with Let's Encrypt for public SSL
./master-deploy.sh --network-type wan
```

#### Hybrid Deployment
```bash
# Deploy with both LAN and WAN access
./master-deploy.sh --network-type hybrid
```

## Management Commands

### Service Management
```bash
# Start/stop/restart services
sudo systemctl start armguard
sudo systemctl stop armguard
sudo systemctl restart armguard
sudo systemctl status armguard

# Enable/disable auto-start
sudo systemctl enable armguard
sudo systemctl disable armguard
```

### Application Updates
```bash
cd /opt/armguard/armguard/deployment/methods/production
sudo ./update-armguard.sh
```

### Backup Management
```bash
# Manual backup
sudo ./secure-backup.sh --manual

# Restore from backup
sudo ./rollback.sh --backup-date 2026-02-01

# List backups
sudo ./secure-backup.sh --list
```

### Health Checks
```bash
# System health check
./health-check.sh

# Detailed status
./deploy-master.sh status

# View logs
sudo journalctl -u armguard -f
```

## Monitoring

### Access Points
- **Application**: `https://your-domain.com`
- **Admin**: `https://your-domain.com/admin`
- **Grafana**: `https://your-domain.com:3000`
- **Prometheus**: `https://your-domain.com:9090`
- **Alertmanager**: `https://your-domain.com:9093`

### Default Credentials
- **Django Admin**: Created during deployment
- **Grafana**: `admin` / `admin` (change on first login)
- **System monitoring**: Automatic configuration

### Alerts Configured
- **High CPU usage** (>80% for 5 minutes)
- **High memory usage** (>90% for 5 minutes)
- **Disk space low** (<10% free space)
- **Service down** (application not responding)
- **Database issues** (connection failures)
- **SSL certificate expiry** (30 days notice)

## Troubleshooting

### Common Issues

**1. SSL Certificate Issues**
```bash
# Renew certificates manually
sudo certbot renew --dry-run

# Check certificate status
sudo certbot certificates

# Regenerate if needed
sudo ./install-mkcert-ssl.sh  # For LAN
# or
sudo certbot --nginx -d your-domain.com  # For WAN
```

**2. Database Connection Issues**
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Test database connection
sudo -u postgres psql -c "\\l"

# Reset database connection
sudo ./setup-database.sh --reset
```

**3. Service Start Issues**
```bash
# Check service logs
sudo journalctl -u armguard -n 50

# Test Gunicorn manually
cd /opt/armguard/armguard
source ../venv/bin/activate
gunicorn --bind 127.0.0.1:8000 core.wsgi:application
```

**4. Nginx Configuration Issues**
```bash
# Test Nginx configuration
sudo nginx -t

# Reload Nginx configuration
sudo nginx -s reload

# Check Nginx logs
sudo tail -f /var/log/nginx/error.log
```

### Performance Optimization

**Database Tuning**
```bash
# Run database optimization
sudo ./setup-database.sh --optimize

# Vacuum and analyze
sudo -u postgres psql armguard_prod -c "VACUUM ANALYZE;"
```

**Application Tuning**
```bash
# Collect and compress static files
cd /opt/armguard/armguard
source ../venv/bin/activate
python manage.py collectstatic --clear
python manage.py compress  # If django-compressor is enabled
```

## Upgrade Process

### Minor Updates
```bash
cd /opt/armguard/armguard/deployment/methods/production
sudo ./update-armguard.sh --minor
```

### Major Updates
```bash
# Create backup first
sudo ./secure-backup.sh --manual

# Run major update
sudo ./update-armguard.sh --major

# Verify deployment
./health-check.sh
```

### Rollback if Needed
```bash
# Rollback to previous version
sudo ./rollback.sh --previous

# Rollback to specific backup
sudo ./rollback.sh --backup-date 2026-02-01
```

## Security Best Practices

### Regular Maintenance
- **Update system packages** monthly
- **Rotate secrets** quarterly
- **Review access logs** weekly
- **Test backups** monthly
- **Security scans** weekly
- **Certificate renewal** automatic

### Monitoring Checklist
- [ ] All services running healthy
- [ ] SSL certificates valid and auto-renewing
- [ ] Backup system functioning
- [ ] Monitoring alerts configured
- [ ] Log retention policies set
- [ ] Performance baselines established

## Support and Documentation

### Additional Resources
- **Network Setup Guide**: [../network_setup/README.md](../network_setup/README.md)
- **Backup Documentation**: [secure-backup.sh](secure-backup.sh)
- **Security Guide**: [secrets-manager.sh](secrets-manager.sh)
- **Health Check Guide**: [health-check.sh](health-check.sh)

### Getting Help
- Use `./deploy-master.sh status` for system overview
- Check `/var/log/armguard/` for application logs
- Review `journalctl -u armguard` for service logs
- Run `./health-check.sh` for detailed diagnostics

This production deployment provides enterprise-grade reliability, security, and monitoring for your ArmGuard application.