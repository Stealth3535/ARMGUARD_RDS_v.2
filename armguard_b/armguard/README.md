# ArmGuard Military Inventory Management System

## 🏆 Production-Ready Django Application

**Status**: ✅ Successfully deployed on Raspberry Pi 4B with HTTPS and device authorization

### 🎯 System Overview

ArmGuard is a comprehensive military inventory management system designed for secure tracking of personnel, equipment, and transactions. Built with Django 5.1.1 and deployed with enterprise-grade security features.

### ✨ Key Features

- 🔐 **Device Authorization** - IP-based transaction restrictions
- 👥 **Personnel Management** - Complete personnel tracking system
- 📦 **Inventory Control** - Equipment and asset management
- 💼 **Transaction Logging** - Comprehensive audit trails
- 📱 **QR Code Integration** - Quick scanning and identification
- 🖨️ **Print Management** - Integrated printing system
- 🔒 **HTTPS Security** - Full SSL/TLS encryption
- 🥧 **Raspberry Pi Ready** - Optimized for ARM64 deployment

### 🚀 Quick Start

#### Prerequisites
- Python 3.10+
- PostgreSQL or SQLite
- Nginx (for production)
- Ubuntu/Debian Linux (recommended)

#### Local Development
```bash
# Clone the repository
git clone https://github.com/yourusername/armguard.git
cd armguard

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env with your settings

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic

# Run development server
python manage.py runserver
```

#### Production Deployment

For production deployment on Raspberry Pi or server:

```bash
cd deployment/organized/active/
sudo ./comprehensive-fix-and-test.sh
```

### 📁 Project Structure

```
armguard/
├── admin/              # Admin interface customizations
├── core/               # Core Django settings and configuration
├── inventory/          # Inventory management app
├── personnel/          # Personnel tracking app
├── transactions/       # Transaction logging app
├── qr_manager/         # QR code generation and scanning
├── print_handler/      # Printing system integration
├── users/              # User management and authentication
├── vpn_integration/    # VPN access integration
├── deployment/         # Deployment scripts and guides
│   └── organized/      # Organized deployment tools
│       ├── active/     # Production-ready scripts
│       ├── docs/       # Complete documentation
│       ├── security/   # Security configuration tools
│       └── archive/    # Historical troubleshooting scripts
└── requirements.txt    # Python dependencies
```

### 🔐 Security Features

- **Device Authorization**: IP-based access control for transactions
- **HTTPS Encryption**: Full SSL/TLS security
- **CSRF Protection**: Cross-site request forgery prevention
- **Session Security**: Secure session management
- **Security Headers**: Comprehensive HTTP security headers
- **Database Security**: Protected database connections

### 🌐 Network Architecture

- **LAN Access**: Full functionality on local network
- **VPN Integration**: Secure remote access via WireGuard
- **Device Restrictions**: Configurable IP-based authorization
- **Mobile Support**: Responsive design for all devices

### 📚 Documentation

Complete documentation available in `/deployment/organized/docs/`:

- [Deployment Guide](deployment/organized/docs/COMPLETE_DEPLOYMENT_GUIDE.md)
- [Operations Manual](deployment/organized/docs/OPERATIONS_MANUAL.md)
- [Security Implementation](deployment/organized/docs/NGINX_SSL_GUIDE.md)
- [Quick Reference](deployment/organized/docs/QUICK_REFERENCE.md)

### 🔧 Development

#### Running Tests
```bash
python manage.py test
```

#### Database Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

#### Collecting Static Files
```bash
python manage.py collectstatic
```

### 🚀 Deployment Options

#### Method 1: Automated Deployment
```bash
cd deployment/
sudo ./deploy-master.sh production
```

#### Method 2: Manual Setup
Follow the comprehensive deployment guide in `/deployment/organized/docs/`

#### Method 3: Docker (Testing)
```bash
cd deployment/methods/docker-testing/
docker-compose up -d
```

### 🔒 HTTPS Setup

Enable HTTPS with multiple certificate options:
```bash
cd deployment/organized/active/
sudo ./enable-https.sh
```

Options:
1. Self-signed certificates (quick setup)
2. mkcert for local development
3. Let's Encrypt for production

### 📊 System Requirements

#### Minimum Requirements
- **CPU**: ARM64 or x86_64
- **RAM**: 2GB (4GB recommended)
- **Storage**: 10GB free space
- **OS**: Ubuntu 20.04+ or Debian 11+
- **Network**: Local network access

#### Production Requirements (Raspberry Pi 4B)
- **Model**: Raspberry Pi 4B (4GB RAM recommended)
- **OS**: Ubuntu Server 22.04 ARM64
- **Storage**: 64GB+ SD card (Class 10)
- **Network**: Ethernet connection recommended

### 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

### 🆘 Support

- 📖 **Documentation**: `/deployment/organized/docs/`
- 🐛 **Issues**: GitHub Issues
- 💬 **Discussions**: GitHub Discussions

### 🏷️ Version

**Current Version**: 2.0.0
- ✅ Production-ready deployment
- ✅ Device authorization implemented
- ✅ HTTPS security enabled
- ✅ Comprehensive documentation
- ✅ Raspberry Pi optimized

### 🎯 Deployment Status

- ✅ **Local Development**: Ready
- ✅ **Production Deployment**: Ready
- ✅ **Security Implementation**: Complete
- ✅ **Documentation**: Complete
- ✅ **Testing**: Validated

### 🔄 Recent Updates

- **February 2026**: Major deployment system reorganization
- **February 2026**: HTTPS implementation with multiple certificate options
- **February 2026**: Device authorization system implementation
- **February 2026**: Comprehensive deployment documentation

---

**ArmGuard** - Secure Military Inventory Management System  
Built with ❤️ for military and security applications