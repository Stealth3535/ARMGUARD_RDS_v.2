# 🗺️ ARMGUARD Deployment Script Flow & Relationships

This document shows how all deployment scripts relate to each other and their execution flows.

---

## 📊 Master Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                    🎯 USER ENTRY POINTS                             │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    │             │             │
          ┌─────────▼────┐  ┌─────▼────┐  ┌────▼──────────┐
          │ ubuntu-      │  │deployment│  │ 01_setup.sh   │
          │ deploy.sh    │  │-helper.sh│  │ 02_config.sh  │
          │              │  │          │  │ 03_services.sh│
          │ (Auto-opt)   │  │(Guide)   │  │ 04_monitor.sh │
          └──────┬───────┘  └─────┬────┘  └────┬──────────┘
                 │                │            │
                 │    ┌───────────┘            │
                 │    │                        │
                 │    │  Calls based on user   │
                 │    │  selection              │
                 │    │                        │
                 ▼    ▼                        ▼
      ┌──────────────────────────────────────────────────┐
      │         DEPLOYMENT IMPLEMENTATIONS               │
      └──────────────────────────────────────────────────┘
                               │
           ┌───────────────────┼──────────────────┐
           │                   │                  │
    ┌──────▼────────┐  ┌───────▼────────┐  ┌────▼──────────┐
    │deploy-        │  │master-         │  │Modular 01-04  │
    │armguard.sh    │  │deploy.sh       │  │               │
    │               │  │                │  │Sequential     │
    │(Full Prod)    │  │(10-Phase Orch) │  │Execution      │
    └───────────────┘  └────────────────┘  └───────────────┘
```

---

## 🔄 Script Relationship Map

### **Level 1: User-Facing Entry Points**

```
ubuntu-deploy.sh ──────────────┐
    │                          │
    ├─ detect_platform()       │
    ├─ check_ubuntu()          │
    ├─ apply_optimizations()   │
    └─ Calls one of: ──────────┼───► methods/basic-setup/serversetup.sh
            │                  │
            │                  ├───► methods/production/deploy-armguard.sh
            │                  │
            └──────────────────┴───► methods/production/master-deploy.sh


deployment-helper.sh ──────────┐
    │                          │
    ├─ Interactive Q&A         │
    ├─ Decision tree           │
    └─ Routes to: ─────────────┼───► 01-04 (modular)
            │                  │
            │                  ├───► methods/production/*
            │                  │
            └──────────────────┴───► methods/docker-testing/*


Modular Scripts (01-04)
    │
    ├─ 01_setup.sh ──────► install packages, setup env
    ├─ 02_config.sh ─────► generate configs, SSL
    ├─ 03_services.sh ───► deploy services  
    └─ 04_monitoring.sh ─► setup monitoring
```

---

## 📦 Modular Scripts (01-04) Detailed Flow

```
┌──────────────────────────────────────────────────────────────┐
│                    01_SETUP.SH                               │
│  Prerequisites & Environment Setup                           │
└──────────────────────────────────────────────────────────────┘
                            │
                            ├─► detect_system_info()
                            │   ├─ OS detection
                            │   ├─ Architecture
                            │   └─ VM detection
                            │
                            ├─► install_system_packages()
                            │   ├─ python3, nginx, redis
                            │   ├─ postgresql/sqlite
                            │   └─ fail2ban, ufw
                            │
                            ├─► setup_python_environment()
                            │   ├─ Create venv
                            │   ├─ Install requirements
                            │   └─ Validate packages
                            │
                            └─► setup_database()
                                ├─ PostgreSQL or SQLite
                                ├─ Create DB
                                └─ Configure Redis
                            │
                            ▼
        Outputs: venv/, packages installed, DB ready
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│                    02_CONFIG.SH                              │
│  Configuration Files & SSL Setup                             │
└──────────────────────────────────────────────────────────────┘
                            │
                            ├─► select_network_type()
                            │   ├─ LAN only
                            │   ├─ WAN only
                            │   └─ Hybrid (LAN+WAN)
                            │
                            ├─► select_ssl_method()
                            │   ├─ mkcert (LAN)
                            │   ├─ Let's Encrypt (WAN)
                            │   └─ Self-signed
                            │
                            ├─► generate_env_file()
                            │   ├─ Django SECRET_KEY
                            │   ├─ Database config
                            │   ├─ Redis password
                            │   └─ Network settings
                            │
                            ├─> configure_ssl_certificates()
                            │   ├─ Install mkcert/certbot
                            │   ├─ Generate certificates
                            │   └─ Setup auto-renewal
                            │
                            └─► configure_nginx()
                                ├─ Create site config
                                ├─ SSL configuration
                                └─ Enable site
                            │
                            ▼
        Outputs: .env file, SSL certs, nginx config
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│                    03_SERVICES.SH                            │
│  Service Deployment & Startup                                │
└──────────────────────────────────────────────────────────────┘
                            │
                            ├─► create_gunicorn_service()
                            │   ├─ Generate systemd unit
                            │   ├─ Calculate workers
                            │   └─ Configure socket
                            │
                            ├─► create_daphne_service()
                            │   ├─ WebSocket support
                            │   └─ ASGI configuration
                            │
                            ├─► run_django_migrations()
                            │   ├─ makemigrations
                            │   ├─ migrate
                            │   └─ collectstatic
                            │
                            └─► start_all_services()
                                ├─ gunicorn-armguard
                                ├─ daphne-armguard
                                ├─ nginx
                                ├─ postgresql
                                └─ redis
                            │
                            ▼
        Outputs: Running services, migrations applied
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│                    04_MONITORING.SH                          │
│  Monitoring & Health Checks                                  │
└──────────────────────────────────────────────────────────────┘
                            │
                            ├─► select_monitoring_type()
                            │   ├─ Minimal (health checks)
                            │   ├─ Operational (metrics)
                            │   └─ Full (Prometheus+Grafana)
                            │
                            ├─► setup_health_checks()
                            │   ├─ Create check scripts
                            │   └─ Schedule cron jobs
                            │
                            ├─► configure_log_rotation()
                            │   ├─ Application logs
                            │   └─ System logs
                            │
                            └─► setup_monitoring_stack()
                                ├─ Install Prometheus (if full)
                                ├─ Install Grafana (if full)
                                └─ Create dashboards
                            │
                            ▼
        Outputs: Monitoring active, health checks running
```

---

## 🏭 Production Scripts Flow

### **deploy-armguard.sh (Complete Production)**

```
deploy-armguard.sh
    │
    ├─ 1. Interactive Configuration
    │     ├─ Project directory (auto-detect git repo!)
    │     ├─ Domain name
    │     ├─ Server IP
    │     ├─ SSL type (mkcert/letsencrypt)
    │     ├─ Database (PostgreSQL/SQLite)
    │     └─ Firewall config
    │
    ├─ 2. install_system_packages()
    │     └─ Same as 01_setup.sh but with prompts
    │
    ├─ 3. setup_project_directory()
    │     ├─ Auto-detect repository
    │     ├─ Offer: use existing vs copy
    │     └─ Validate manage.py exists
    │
    ├─ 4. setup_python_environment()
    │     └─ venv creation + requirements install
    │
    ├─ 5. setup_database()
    │     ├─ PostgreSQL with optimization
    │     └─ Or SQLite
    │
    ├─ 6. configure_django()
    │     ├─ Generate SECRET_KEY
    │     ├─ Settings validation
    │     └─ Migrations
    │
    ├─ 7. install_gunicorn_service()
    │     └─ Systemd unit creation
    │
    ├─ 8. configure_nginx()
    │     ├─ Site configuration
    │     ├─ SSL setup
    │     └─ Security headers
    │
    ├─ 9. configure_firewall()
    │     ├─ UFW rules
    │     └─ Port configuration
    │
    └─ 10. final_checks()
          ├─ Service verification
          └─ SSL certificate check
```

### **master-deploy.sh (Orchestrated 10-Phase)**

```
master-deploy.sh
    │
    ├─ Load config from master-config.sh
    │
    ├─ Check for integrated network (02_config.sh)
    │
    ├─ Parse arguments (--network-type, etc.)
    │
    ├─ Display configuration summary
    │
    └─ Execute 10 phases:
        │
        ├─ Phase 1: detect-environment.sh
        │     └─ Detect system capabilities
        │
        ├─ Phase 2: install-dependencies.sh
        │     └─ System packages
        │
        ├─ Phase 3: setup-python-env.sh
        │     └─ Virtual env + requirements
        │
        ├─ Phase 4: setup-database.sh
        │     ├─ DB creation
        │     └─ Run migrations
        │
        ├─ Phase 5: install-gunicorn-service.sh
        │     └─ Gunicorn systemd unit
        │
        ├─ Phase 6: configure-nginx.sh
        │     └─ Nginx reverse proxy
        │
        ├─ Phase 7: setup-ssl.sh
        │     └─ SSL certificates
        │
        ├─ Phase 8: configure-firewall.sh
        │     └─ UFW/iptables rules
        │
        ├─ Phase 9: setup-logrotate.sh
        │     └─ Log rotation
        │
        └─ Phase 10: health-check.sh
              └─ Verify deployment
```

---

## 🔧 Shared Utilities & Configuration

### **master-config.sh**
```
master-config.sh (Central Configuration)
    │
    ├─ Sourced by:
    │   ├─ 01_setup.sh
    │   ├─ 02_config.sh
    │   ├─ 03_services.sh
    │   ├─ 04_monitoring.sh
    │   ├─ master-deploy.sh
    │   └─ All production scripts
    │
    └─ Provides:
        ├─ PROJECT_NAME
        ├─ PROJECT_DIR
        ├─ SERVICE_NAME
        ├─ Network settings
        └─ Default ports
```

### **unified-env-generator.ps1**
```
unified-env-generator.ps1
    │
    ├─ Generates .env file with:
    │   ├─ DJANGO_SECRET_KEY (auto-generated)
    │   ├─ DATABASE settings
    │   ├─ REDIS configuration
    │   ├─ NETWORK_TYPE
    │   └─ 50+ environment variables
    │
    └─ Called by: 02_config.sh
```

### **sync-validator.ps1**
```
sync-validator.ps1  
    │
    ├─ Validates:
    │   ├─ File synchronization
    │   ├─ Configuration consistency
    │   ├─ Requirements alignment
    │   └─ Deployment readiness
    │
    └─ Run before: Any major deployment
```

---

## 🎯 Decision Logic

### **ubuntu-deploy.sh Decision Tree**

```
ubuntu-deploy.sh
    │
    ├─ Detect platform
    │   ├─ x86_64? → HP ProDesk? → Optimize for mini PC
    │   ├─ ARM64? → Raspberry Pi? → Optimize for Pi
    │   └─ Standard server → Standard optimization
    │
    ├─ Calculate resources
    │   ├─ CPU cores → Worker count
    │   └─ RAM → Database choice (PostgreSQL/SQLite)
    │
    ├─ Mode selection
    │   ├─ --quick → basic-setup/serversetup.sh
    │   ├─ --production → production/deploy-armguard.sh
    │   └─ standard → production/master-deploy.sh
    │
    └─ Execute selected deployment
```

### **deployment-helper.sh Decision Tree**

```
deployment-helper.sh
    │
    ├─ Question 1: Purpose?
    │   ├─ Development → 01-04 scripts (minimal monitoring)
    │   ├─ Production → Ask Question 2
    │   ├─ Enterprise → production/master-deploy.sh
    │   ├─ Testing → docker-testing/
    │   ├─ Network separation → master-deploy.sh --network-type
    │   └─ VMware → vmware-setup/ + 01-04
    │
    └─ Question 2: Monitoring level?  
        ├─ Minimal → 04_monitoring.sh (minimal)
        ├─ Operational → 04_monitoring.sh (operational)
        └─ Full → 04_monitoring.sh (full stack)
```

---

## 📈 Execution Order Dependencies

### **Sequential Dependencies**

```
MUST run in order:
    01_setup.sh
       ↓ (requires system packages)
    02_config.sh
       ↓ (requires .env and configs)
    03_services.sh
       ↓ (requires services running)
    04_monitoring.sh
```

### **Parallel Safe Operations**

```
Can run in parallel:
    - sync-validator.ps1 (before any deployment)
    - health-check.sh (after deployment)
    - detect-environment.sh (standalone)
```

### **Order-Independent**

```
Can run anytime:
    - deployment-helper.sh (guides only)
    - ubuntu-deploy.sh (self-contained)
    - deploy-armguard.sh (self-contained)
```

---

## 🔄 Update & Re-deployment Flow

```
After git pull origin main:
    │
    ├─ Config unchanged?
    │   └─ Yes → Just restart services
    │       └─ systemctl restart gunicorn-armguard nginx
    │
    ├─ Dependencies changed?
    │   └─ Yes → Re-run 01_setup.sh
    │       └─ Then restart services
    │
    ├─ Configuration changed?
    │   └─ Yes → Re-run 02_config.sh
    │       └─ Then restart services
    │
    └─ Database schema changed?
        └─ Yes → Run migrations
            ├─ python manage.py migrate
            └─ systemctl restart gunicorn-armguard
```

---

## 🎬 Common Workflows

### **First-Time Deployment**
```
ubuntu-deploy.sh --production
    OR
01_setup.sh → 02_config.sh → 03_services.sh → 04_monitoring.sh
```

### **Development Setup**
```
01_setup.sh → 02_config.sh → 03_services.sh
(Skip monitoring)
```

### **Production with Network Isolation**
```
master-deploy.sh --network-type hybrid
```

### **Quick Update**
```
git pull
pip install -r requirements.txt
python manage.py migrate
systemctl restart gunicorn-armguard
```

### **Full Re-deployment**
```
Stop all services
Re-run: deploy-armguard.sh
    OR
Re-run: 01-04 scripts
```

---

## 📊 Integration Points

```
┌─────────────────┐
│ Entry Scripts   │
└────────┬────────┘
         │
    ┌────▼─────────────────┐
    │ master-config.sh     │ ◄─── Shared config
    └────┬─────────────────┘
         │
    ┌────▼──────────────────────┐
    │ Implementation Scripts    │
    │ - deploy-armguard.sh      │
    │ - master-deploy.sh        │
    │ - 01-04 modular           │
    └────┬──────────────────────┘
         │
    ┌────▼──────────────────────┐
    │ Utility Scripts           │
    │ - detect-environment.sh   │
    │ - health-check.sh         │
    │ - install-*-service.sh    │
    └───────────────────────────┘
```

---

This completes the comprehensive flow and relationship documentation for the ARMGUARD deployment system!
