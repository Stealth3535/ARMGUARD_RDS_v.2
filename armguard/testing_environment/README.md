# ArmGuard Testing Environment

A comprehensive Docker-based testing environment for the ArmGuard military armory management system. This environment simulates real-world conditions and enables testing of functionality, security, and operational resilience.

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Testing Environment                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐      │
│  │  Nginx   │────│  Django  │────│ PostgreSQL│    │  Redis   │      │
│  │  (SSL)   │    │   App    │    │    DB     │    │  Cache   │      │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘      │
│       │                │                                              │
│       │                │                                              │
│  ┌────┴────────────────┴────────────────────────────────────┐       │
│  │                    Monitoring Stack                        │       │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │       │
│  │  │Prometheus│  │ Grafana  │  │Alertmgr  │  │  Loki    │ │       │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘ │       │
│  └──────────────────────────────────────────────────────────┘       │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────┐       │
│  │                    Testing Stack                           │       │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │       │
│  │  │ Selenium │  │OWASP ZAP │  │  Locust  │  │Test Runner│ │       │
│  │  │   Grid   │  │ Scanner  │  │  Master  │  │  (pytest) │ │       │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘ │       │
│  └──────────────────────────────────────────────────────────┘       │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

## 📋 Prerequisites

- Docker 24.0+ and Docker Compose 2.20+
- 8GB+ RAM available for Docker
- 20GB+ free disk space
- Git for version control

## 🚀 Quick Start

### 1. Generate SSL Certificates

```bash
cd testing_environment/nginx/ssl
chmod +x generate-certs.sh
./generate-certs.sh
```

### 2. Start Core Services

```bash
cd testing_environment
docker compose up -d armguard-db armguard-redis armguard-app nginx
```

### 3. Verify Application Health

```bash
# Wait for services to be ready
docker compose ps

# Check application health
curl -k https://localhost/health/
```

### 4. Start Monitoring (Optional)

```bash
docker compose --profile monitoring up -d
```

### 5. Start Testing Tools (Optional)

```bash
docker compose --profile testing up -d
```

## 📁 Directory Structure

```
testing_environment/
├── docker-compose.yml          # Main orchestration file
├── Dockerfile                  # Django app container
├── docker-entrypoint.sh        # Container initialization
├── .env.example                # Environment variables template
├── README.md                   # This file
│
├── nginx/
│   ├── nginx.conf              # Nginx configuration
│   └── ssl/
│       └── generate-certs.sh   # SSL certificate generator
│
├── monitoring/
│   ├── prometheus/
│   │   ├── prometheus.yml      # Prometheus configuration
│   │   └── alerts.yml          # Alert rules
│   ├── alertmanager/
│   │   └── alertmanager.yml    # Alert routing
│   ├── loki/
│   │   └── loki-config.yml     # Log aggregation
│   ├── promtail/
│   │   └── promtail-config.yml # Log collection
│   └── grafana/
│       └── provisioning/
│           └── datasources/
│               └── datasources.yml
│
├── functional_tests/
│   ├── test_functional.py      # Selenium UI tests
│   └── test_api.py             # API endpoint tests
│
├── security_tests/
│   ├── run_security_scan.sh    # Security scan orchestrator
│   └── zap/
│       ├── zap-config.yaml     # ZAP configuration
│       └── zap-rules.tsv       # Scan rules
│
├── performance_tests/
│   ├── locustfile.py           # Load test scenarios
│   └── run_load_tests.sh       # Performance test runner
│
└── .github/
    └── workflows/
        └── test.yml            # CI/CD pipeline
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file from the template:

```bash
cp .env.example .env
```

Key variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `DJANGO_SECRET_KEY` | Django secret key | (generated) |
| `DEBUG` | Debug mode | False |
| `POSTGRES_DB` | Database name | armguard |
| `POSTGRES_USER` | Database user | armguard_user |
| `POSTGRES_PASSWORD` | Database password | (set in .env) |
| `REDIS_URL` | Redis connection URL | redis://armguard-redis:6379/0 |
| `GRAFANA_ADMIN_PASSWORD` | Grafana admin password | admin |
| `ALERT_SLACK_WEBHOOK` | Slack webhook for alerts | (optional) |

### Docker Compose Profiles

| Profile | Services | Use Case |
|---------|----------|----------|
| (default) | app, db, redis, nginx | Core application |
| `monitoring` | prometheus, grafana, alertmanager, loki, promtail | Observability |
| `testing` | selenium, zap, locust, test-runner | Testing tools |

## 🧪 Running Tests

### Functional Tests

```bash
# Start application and Selenium Grid
docker compose up -d armguard-app nginx
docker compose --profile testing up -d selenium-hub selenium-chrome

# Run functional tests
docker compose run --rm test-runner pytest /tests/functional_tests/ -v

# Or run specific tests
docker compose run --rm test-runner pytest /tests/functional_tests/test_functional.py -v -k "test_login"
```

### Security Tests

```bash
# Start application
docker compose up -d armguard-app nginx

# Run ZAP baseline scan
docker compose run --rm zap zap-baseline.py \
    -t https://nginx \
    -r zap-report.html

# Run comprehensive security scan
docker compose run --rm security-runner bash /security_tests/run_security_scan.sh
```

### Performance Tests

```bash
# Start application
docker compose up -d armguard-app nginx

# Run with Web UI (accessible at http://localhost:8089)
docker compose --profile testing up -d locust-master locust-worker

# Run headless load test
docker compose run --rm locust-master locust \
    -f /locust/locustfile.py \
    --headless \
    --host=https://nginx \
    --users=50 \
    --spawn-rate=5 \
    --run-time=5m
```

### All Tests (CI/CD style)

```bash
# Run complete test suite
./run_all_tests.sh
```

## 📊 Monitoring & Dashboards

### Accessing Dashboards

| Service | URL | Credentials |
|---------|-----|-------------|
| Grafana | http://localhost:3000 | admin / (see .env) |
| Prometheus | http://localhost:9090 | - |
| Alertmanager | http://localhost:9093 | - |
| Locust UI | http://localhost:8089 | - |
| Selenium Grid | http://localhost:4444 | - |

### Pre-configured Grafana Dashboards

1. **Application Overview** - Request rates, latencies, errors
2. **Infrastructure** - CPU, memory, disk usage
3. **Security Events** - Authentication failures, rate limiting
4. **Performance** - Response times, throughput

### Alert Rules

| Alert | Severity | Condition |
|-------|----------|-----------|
| HighErrorRate | Critical | Error rate > 5% for 5 min |
| SlowResponses | Warning | 95th percentile > 2s |
| HighMemoryUsage | Warning | Memory > 80% |
| DatabaseDown | Critical | PostgreSQL unreachable |
| TooManyLoginFailures | Warning | > 10 failures/min |

## 🔐 Security Testing Details

### OWASP ZAP Scans

The security test suite runs:

1. **Baseline Scan** - Passive scanning for common issues
2. **Active Scan** - Aggressive testing for vulnerabilities
3. **API Scan** - Tests REST API endpoints
4. **Authentication Scan** - Tests login security

### Security Checks Performed

- SQL Injection
- Cross-Site Scripting (XSS)
- Cross-Site Request Forgery (CSRF)
- Security Headers
- SSL/TLS Configuration
- Authentication Bypass
- Session Management
- Access Control

### Custom Security Tests

Additional checks in `run_security_scan.sh`:

- Rate limiting validation
- Password policy enforcement
- Session timeout verification
- CORS configuration
- Cookie security attributes

## 📈 Performance Testing Details

### Load Test Scenarios

| User Type | Weight | Actions |
|-----------|--------|---------|
| Regular User | 60% | Dashboard, personnel view, inventory browse |
| Admin User | 30% | Reports, user management, configuration |
| Anonymous | 10% | Login attempts, public pages |

### Performance Thresholds

| Metric | Excellent | Good | Acceptable | Poor |
|--------|-----------|------|------------|------|
| Response Time | < 200ms | < 500ms | < 1000ms | < 2000ms |
| Failure Rate | < 0.1% | < 0.5% | < 1% | < 5% |
| Throughput | > 100 rps | > 50 rps | > 25 rps | > 10 rps |

## 🔄 CI/CD Integration

### GitHub Actions Workflow

The included workflow (`.github/workflows/test.yml`) runs:

1. **Build** - Lint, unit tests, security scan
2. **Functional Tests** - Selenium-based UI tests
3. **Security Tests** - OWASP ZAP scanning
4. **Performance Tests** - Locust load testing
5. **Report Generation** - Consolidated test report

### Manual Trigger Options

```bash
# Run all tests
gh workflow run test.yml -f test_type=all

# Run only security tests
gh workflow run test.yml -f test_type=security

# Run performance tests with custom user count
gh workflow run test.yml -f test_type=performance -f performance_users=100
```

## 🛠️ Troubleshooting

### Common Issues

#### Services won't start

```bash
# Check logs
docker compose logs -f armguard-app

# Rebuild containers
docker compose build --no-cache

# Reset everything
docker compose down -v
docker compose up -d
```

#### Database connection issues

```bash
# Check database is running
docker compose exec armguard-db pg_isready

# Check logs
docker compose logs armguard-db
```

#### SSL certificate errors

```bash
# Regenerate certificates
cd nginx/ssl
./generate-certs.sh

# Restart nginx
docker compose restart nginx
```

#### Tests failing with timeout

```bash
# Increase wait times in tests
export SELENIUM_TIMEOUT=30

# Check application is responding
curl -k https://localhost/health/
```

### Useful Commands

```bash
# View all container status
docker compose ps -a

# Enter a container
docker compose exec armguard-app bash

# View real-time logs
docker compose logs -f

# Reset database
docker compose exec armguard-app python manage.py flush

# Run Django management commands
docker compose exec armguard-app python manage.py [command]
```

## 📝 Test Report Template

See [TEST_REPORT_TEMPLATE.md](./TEST_REPORT_TEMPLATE.md) for the standard test report format.

## 🤝 Contributing

1. Create a feature branch
2. Make changes
3. Run the test suite locally
4. Submit a pull request
5. CI/CD will validate changes

## 📚 Additional Resources

- [Django Testing Documentation](https://docs.djangoproject.com/en/5.0/topics/testing/)
- [OWASP Testing Guide](https://owasp.org/www-project-web-security-testing-guide/)
- [Locust Documentation](https://docs.locust.io/)
- [Prometheus Alerting](https://prometheus.io/docs/alerting/latest/overview/)

---

*ArmGuard Testing Environment v1.0*
