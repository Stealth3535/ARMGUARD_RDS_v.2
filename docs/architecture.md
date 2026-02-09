# ARMGUARD - System Architecture

## Table of Contents
- [Architecture Overview](#architecture-overview)
- [System Components](#system-components)
- [Frontend Architecture](#frontend-architecture)
- [Backend Architecture](#backend-architecture)
- [Database Design](#database-design)
- [API Architecture](#api-architecture)
- [Real-time Communication](#real-time-communication)
- [Security Architecture](#security-architecture)
- [Network Architecture](#network-architecture)
- [Deployment Architecture](#deployment-architecture)
- [Scalability Considerations](#scalability-considerations)
- [Performance Architecture](#performance-architecture)

## Architecture Overview

ARMGUARD follows a modern **n-tier architecture** designed for military-grade security, reliability, and performance. The system implements a **layered security model** with **network-based access controls** and **comprehensive audit logging**.

### Architectural Patterns
- **Model-View-Controller (MVC)**: Django's MVT pattern for clean separation of concerns
- **Service-Oriented Architecture**: Modular app structure with dedicated services
- **Event-Driven Architecture**: Real-time updates via WebSocket events
- **Repository Pattern**: Database abstraction with custom managers
- **Middleware Pattern**: Request/response processing pipeline

### Design Principles
1. **Security First**: Every component designed with security as primary concern
2. **Fail-Safe Operation**: Graceful degradation and error handling
3. **Audit Transparency**: Complete activity tracking and logging
4. **Network Isolation**: LAN-only sensitive operations
5. **Modular Design**: Loosely coupled, highly cohesive components

## System Components

### High-Level Architecture Diagram

```mermaid
graph TB
    subgraph "Client Tier"
        WEB[Web Browser]
        MOBILE[Mobile Device]
        QR[QR Scanner]
    end
    
    subgraph "Presentation Tier"
        NGINX[Nginx Reverse Proxy]
        SSL[SSL/TLS Termination]
        LB[Load Balancer]
    end
    
    subgraph "Application Tier"
        DJANGO[Django Framework]
        WSGI[WSGI Server - Gunicorn]
        ASGI[ASGI Server - Daphne]
        MIDDLEWARE[Security Middleware Stack]
    end
    
    subgraph "Service Tier"
        AUTH[Authentication Service]
        INVENTORY[Inventory Service]
        PERSONNEL[Personnel Service]
        TRANSACTION[Transaction Service]
        QR_MGR[QR Manager Service]
        WEBSOCKET[WebSocket Service]
    end
    
    subgraph "Data Tier"
        POSTGRES[(PostgreSQL)]
        REDIS[(Redis Cache)]
        FILES[File Storage]
    end
    
    subgraph "Security Tier"
        AUTHZ[Authorization]
        AUDIT[Audit Logging]
        RATE[Rate Limiting]
        NETWORK[Network Access Control]
    end
    
    WEB --> NGINX
    MOBILE --> NGINX
    QR --> NGINX
    
    NGINX --> SSL
    SSL --> LB
    LB --> WSGI
    LB --> ASGI
    
    WSGI --> DJANGO
    ASGI --> WEBSOCKET
    DJANGO --> MIDDLEWARE
    
    MIDDLEWARE --> AUTH
    MIDDLEWARE --> INVENTORY
    MIDDLEWARE --> PERSONNEL
    MIDDLEWARE --> TRANSACTION
    MIDDLEWARE --> QR_MGR
    
    AUTH --> POSTGRES
    INVENTORY --> POSTGRES
    PERSONNEL --> POSTGRES
    TRANSACTION --> POSTGRES
    QR_MGR --> FILES
    
    DJANGO --> REDIS
    WEBSOCKET --> REDIS
    
    MIDDLEWARE --> AUTHZ
    MIDDLEWARE --> AUDIT
    MIDDLEWARE --> RATE
    MIDDLEWARE --> NETWORK
    
    AUTHZ --> POSTGRES
    AUDIT --> POSTGRES
    RATE --> REDIS
    NETWORK --> REDIS
```

### Component Responsibilities

#### Client Tier Components
- **Web Browser**: Primary user interface for desktop/laptop access
- **Mobile Device**: Touch-optimized interface for mobile access
- **QR Scanner**: Camera-based QR code scanning functionality

#### Presentation Tier Components
- **Nginx**: Reverse proxy, static file serving, SSL termination
- **Load Balancer**: Traffic distribution and high availability
- **SSL/TLS**: Encryption for all communications

#### Application Tier Components
- **Django Framework**: Core web application framework
- **WSGI Server (Gunicorn)**: HTTP request handling for Django
- **ASGI Server (Daphne)**: WebSocket and async request handling
- **Middleware Stack**: Request/response processing pipeline

#### Service Tier Components
- **Authentication Service**: User login, session management
- **Inventory Service**: Weapons and equipment management
- **Personnel Service**: Military personnel management
- **Transaction Service**: Weapon withdrawal/return processing
- **QR Manager Service**: QR code generation and management
- **WebSocket Service**: Real-time communication handling

## Frontend Architecture

### Client-Side Architecture

```mermaid
graph TB
    subgraph "Web Client Architecture"
        HTML[HTML Templates]
        CSS[CSS Stylesheets]
        JS[JavaScript Logic]
        
        subgraph "UI Components"
            DASHBOARD[Dashboard Components]
            FORMS[Form Components]
            TABLES[Table Components]
            MODALS[Modal Components]
            QR_SCAN[QR Scanner Component]
        end
        
        subgraph "Communication Layer"
            AJAX[AJAX Requests]
            WEBSOCKET_CLIENT[WebSocket Client]
            CSRF[CSRF Token Management]
        end
        
        subgraph "State Management"
            LOCAL_STORAGE[LocalStorage]
            SESSION_STORAGE[SessionStorage]
            DOM_STATE[DOM State]
        end
    end
    
    HTML --> DASHBOARD
    HTML --> FORMS
    HTML --> TABLES
    HTML --> MODALS
    
    CSS --> DASHBOARD
    CSS --> FORMS
    CSS --> TABLES
    CSS --> MODALS
    
    JS --> QR_SCAN
    JS --> AJAX
    JS --> WEBSOCKET_CLIENT
    JS --> CSRF
    
    AJAX --> LOCAL_STORAGE
    WEBSOCKET_CLIENT --> SESSION_STORAGE
    JS --> DOM_STATE
```

### Frontend Technology Stack
- **Template Engine**: Django Templates with template inheritance
- **CSS Framework**: Bootstrap 5.3 with custom military theme
- **JavaScript**: Vanilla ES6+ with WebSocket API
- **Icons**: FontAwesome 6.0 professional icon set
- **QR Scanner**: HTML5 Camera API with qrcode.js library
- **Charts/Graphs**: Chart.js for dashboard analytics
- **Progressive Web App**: Service worker for offline capability

### Responsive Design Architecture
```mermaid
graph LR
    subgraph "Breakpoints"
        XS[Extra Small<br/>< 576px]
        SM[Small<br/>576px - 768px]
        MD[Medium<br/>768px - 992px]
        LG[Large<br/>992px - 1200px]
        XL[Extra Large<br/>> 1200px]
    end
    
    subgraph "Layout Adaptations"
        MOBILE[Mobile Layout<br/>Single Column]
        TABLET[Tablet Layout<br/>Two Columns]
        DESKTOP[Desktop Layout<br/>Multi-Column]
    end
    
    XS --> MOBILE
    SM --> MOBILE
    MD --> TABLET
    LG --> DESKTOP
    XL --> DESKTOP
```

## Backend Architecture

### Django Application Structure

```mermaid
graph TB
    subgraph "Django Project: core"
        SETTINGS[Settings]
        URLS[URL Configuration]
        WSGI[WSGI Configuration]
        ASGI[ASGI Configuration]
    end
    
    subgraph "Django Apps"
        ADMIN_APP[admin - System Administration]
        CORE_APP[core - Core Functionality]
        USERS_APP[users - User Management]
        PERSONNEL_APP[personnel - Personnel Management]
        INVENTORY_APP[inventory - Inventory Management]
        TRANSACTIONS_APP[transactions - Transaction Processing]
        QR_MANAGER_APP[qr_manager - QR Code Management]
        PRINT_HANDLER_APP[print_handler - Document Generation]
        VPN_INTEGRATION_APP[vpn_integration - VPN Support]
    end
    
    subgraph "Shared Components"
        MIDDLEWARE[Custom Middleware]
        VALIDATORS[Data Validators]
        UTILITIES[Utility Functions]
        TEMPLATES[Template System]
        STATIC[Static Files]
    end
    
    CORE_APP --> SETTINGS
    CORE_APP --> URLS
    CORE_APP --> WSGI
    CORE_APP --> ASGI
    
    ADMIN_APP --> MIDDLEWARE
    USERS_APP --> MIDDLEWARE
    PERSONNEL_APP --> MIDDLEWARE
    INVENTORY_APP --> MIDDLEWARE
    TRANSACTIONS_APP --> MIDDLEWARE
    QR_MANAGER_APP --> MIDDLEWARE
    PRINT_HANDLER_APP --> MIDDLEWARE
    VPN_INTEGRATION_APP --> MIDDLEWARE
    
    MIDDLEWARE --> VALIDATORS
    MIDDLEWARE --> UTILITIES
    MIDDLEWARE --> TEMPLATES
    MIDDLEWARE --> STATIC
```

### Application Module Details

#### Core Application Structure
```python
core/
├── __init__.py
├── settings.py              # Django settings with security optimizations
├── urls.py                  # Main URL configuration
├── wsgi.py                  # WSGI server configuration
├── asgi.py                  # ASGI server configuration for WebSockets
├── middleware/              # Custom middleware components
│   ├── security_middleware.py
│   ├── audit_middleware.py
│   ├── network_middleware.py
│   └── performance.py
├── templates/               # Base templates
├── static/                  # Static assets
├── views.py                 # Core views (dashboard, login)
├── utils.py                 # Utility functions
├── validator.py             # Data validation
└── network_decorators.py    # Network access decorators
```

#### Service-Oriented Module Architecture
Each Django app follows consistent structure:

```python
app_name/
├── __init__.py
├── models.py               # Data models with audit logging
├── views.py                # Class-based and function-based views
├── urls.py                 # URL routing for the app
├── forms.py                # Form definitions and validation
├── admin.py                # Django admin configuration
├── signals.py              # Django signal handlers
├── apps.py                 # App configuration
├── migrations/             # Database migrations
├── templates/app_name/     # App-specific templates
├── static/app_name/        # App-specific static files
└── tests.py                # Unit and integration tests
```

### Request Processing Pipeline

```mermaid
sequenceDiagram
    participant Client
    participant Nginx
    participant Django
    participant Middleware
    participant View
    participant Model
    participant Database
    participant Cache
    
    Client->>Nginx: HTTP Request
    Nginx->>Django: Forward Request
    Django->>Middleware: Process Request
    
    Middleware->>Middleware: Security Check
    Middleware->>Middleware: Authentication
    Middleware->>Middleware: Network Access Control
    Middleware->>Middleware: Rate Limiting
    Middleware->>Middleware: Audit Logging
    
    Middleware->>View: Authorized Request
    View->>Cache: Check Cache
    alt Cache Hit
        Cache->>View: Cached Data
    else Cache Miss
        View->>Model: Query Data
        Model->>Database: SQL Query
        Database->>Model: Result Set
        Model->>View: Python Objects
        View->>Cache: Store Result
    end
    
    View->>Middleware: Response
    Middleware->>Django: Process Response
    Django->>Nginx: HTTP Response
    Nginx->>Client: Final Response
```

## Database Design

### Entity Relationship Diagram

```mermaid
erDiagram
    PERSONNEL {
        string id PK
        string surname
        string firstname
        string middle_initial
        string rank
        string serial UK
        string group_field
        string classification
        string status
        string telephone
        string picture
        string qr_code
        datetime created_at
        datetime updated_at
        datetime deleted_at
        int created_by FK
        int modified_by FK
    }
    
    ITEM {
        string id PK
        string item_type
        string serial UK
        text description
        string condition
        string status
        date registration_date
        string qr_code
        datetime created_at
        datetime updated_at
    }
    
    TRANSACTION {
        int id PK
        string personnel_id FK
        string item_id FK
        int issued_by FK
        string action
        datetime date_time
        int mags
        int rounds
        string duty_type
        text notes
        datetime created_at
        datetime updated_at
    }
    
    USER {
        int id PK
        string username UK
        string email
        string first_name
        string last_name
        string password
        boolean is_staff
        boolean is_superuser
        datetime date_joined
        datetime last_login
    }
    
    USERPROFILE {
        int id PK
        int user_id FK
        string role
        text authorized_devices
        datetime last_device_check
        datetime created_at
        datetime updated_at
    }
    
    QRCODEIMAGE {
        int id PK
        string qr_type
        string reference_id
        string qr_data
        string qr_image_path
        datetime created_at
        datetime updated_at
    }
    
    AUDITLOG {
        int id PK
        string model_name
        string object_id
        string action
        text changes
        int user_id FK
        string ip_address
        string user_agent
        datetime timestamp
    }
    
    DELETEDRECORD {
        int id PK
        string original_model
        string original_id
        text original_data
        int deleted_by FK
        datetime deleted_at
        string deletion_reason
    }
    
    USER ||--o| USERPROFILE : has
    USER ||--o{ PERSONNEL : creates
    USER ||--o{ PERSONNEL : modifies
    USER ||--o{ TRANSACTION : processes
    USER ||--o{ AUDITLOG : generates
    USER ||--o{ DELETEDRECORD : creates
    
    PERSONNEL ||--o{ TRANSACTION : participates
    ITEM ||--o{ TRANSACTION : involved
    
    PERSONNEL ||--o| QRCODEIMAGE : has_qr
    ITEM ||--o| QRCODEIMAGE : has_qr
```

### Database Optimization Features

#### Indexing Strategy
```sql
-- Personnel table indexes
CREATE INDEX idx_personnel_status_group ON personnel(status, group_field);
CREATE INDEX idx_personnel_serial ON personnel(serial);
CREATE INDEX idx_personnel_deleted_at ON personnel(deleted_at);

-- Item table indexes  
CREATE INDEX idx_item_type_status ON items(item_type, status);
CREATE INDEX idx_item_serial ON items(serial);

-- Transaction table indexes
CREATE INDEX idx_transaction_date_time ON transactions(date_time DESC);
CREATE INDEX idx_transaction_personnel_date ON transactions(personnel_id, date_time DESC);
CREATE INDEX idx_transaction_item_date ON transactions(item_id, date_time DESC);

-- Audit log indexes
CREATE INDEX idx_auditlog_timestamp ON admin_auditlog(timestamp DESC);
CREATE INDEX idx_auditlog_model_object ON admin_auditlog(model_name, object_id);
CREATE INDEX idx_auditlog_user_timestamp ON admin_auditlog(user_id, timestamp DESC);
```

#### Query Optimization Features
- **Select Related**: Automatic foreign key optimization
- **Prefetch Related**: Optimized M2M and reverse FK queries
- **Database Query Caching**: Redis-based query result caching
- **Connection Pooling**: PostgreSQL connection reuse
- **Read Replicas**: Support for read-only database replicas

## API Architecture

### RESTful API Design

```mermaid
graph TB
    subgraph "API Endpoints"
        PERSONNEL_API[Personnel API<br/>/api/personnel/]
        INVENTORY_API[Inventory API<br/>/api/inventory/]
        TRANSACTION_API[Transaction API<br/>/api/transactions/]
        QR_API[QR Code API<br/>/api/qr/]
        AUTH_API[Authentication API<br/>/api/auth/]
    end
    
    subgraph "API Features"
        PAGINATION[Pagination]
        FILTERING[Filtering]
        SEARCH[Search]
        ORDERING[Ordering]
        SERIALIZATION[JSON Serialization]
    end
    
    subgraph "Security"
        TOKEN_AUTH[Token Authentication]
        PERMISSIONS[API Permissions]
        RATE_LIMIT[API Rate Limiting]
        CORS[CORS Headers]
        CSRF_API[CSRF Protection]
    end
    
    PERSONNEL_API --> PAGINATION
    INVENTORY_API --> FILTERING
    TRANSACTION_API --> SEARCH
    QR_API --> ORDERING
    AUTH_API --> SERIALIZATION
    
    PERSONNEL_API --> TOKEN_AUTH
    INVENTORY_API --> PERMISSIONS
    TRANSACTION_API --> RATE_LIMIT
    QR_API --> CORS
    AUTH_API --> CSRF_API
```

### API Endpoint Structure

#### Personnel Management API
```python
# URL: /api/personnel/
GET     /api/personnel/              # List all personnel
POST    /api/personnel/              # Create new personnel
GET     /api/personnel/{id}/         # Get specific personnel
PUT     /api/personnel/{id}/         # Update personnel
PATCH   /api/personnel/{id}/         # Partial update
DELETE  /api/personnel/{id}/         # Soft delete personnel

# Additional endpoints
GET     /api/personnel/search/       # Search personnel
GET     /api/personnel/by-qr/        # Lookup by QR code
POST    /api/personnel/bulk/         # Bulk operations
```

#### Inventory Management API
```python
# URL: /api/inventory/
GET     /api/inventory/              # List all items
POST    /api/inventory/              # Register new item
GET     /api/inventory/{id}/         # Get specific item
PUT     /api/inventory/{id}/         # Update item
PATCH   /api/inventory/{id}/         # Partial update
DELETE  /api/inventory/{id}/         # Remove item

# Status management
PATCH   /api/inventory/{id}/status/  # Update item status
GET     /api/inventory/available/    # Available items only
GET     /api/inventory/issued/       # Issued items only
```

#### Transaction Processing API
```python
# URL: /api/transactions/
GET     /api/transactions/           # List transactions
POST    /api/transactions/           # Create transaction
GET     /api/transactions/{id}/      # Get transaction details
POST    /api/transactions/qr/        # QR-based transaction
POST    /api/transactions/return/    # Process return

# Reporting endpoints
GET     /api/transactions/report/    # Generate reports
GET     /api/transactions/audit/     # Audit trail
```

### API Response Format

#### Standard Success Response
```json
{
  "success": true,
  "data": {
    "id": "PE-12345678-090226",
    "surname": "Smith",
    "firstname": "John",
    "rank": "SGT",
    "status": "Active"
  },
  "meta": {
    "timestamp": "2026-02-09T10:30:00Z",
    "version": "1.0"
  }
}
```

#### Standard Error Response
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid data provided",
    "details": {
      "serial": ["This serial number is already in use"],
      "rank": ["Invalid rank specified"]
    }
  },
  "meta": {
    "timestamp": "2026-02-09T10:30:00Z",
    "version": "1.0"
  }
}
```

#### Paginated Response
```json
{
  "success": true,
  "data": [...],
  "pagination": {
    "page": 1,
    "per_page": 25,
    "total_pages": 4,
    "total_count": 87,
    "has_next": true,
    "has_prev": false
  }
}
```

## Real-time Communication

### WebSocket Architecture

```mermaid
graph TB
    subgraph "WebSocket Client"
        BROWSER[Browser WebSocket]
        RECONNECT[Auto Reconnection]
        HEARTBEAT[Heartbeat Monitor]
    end
    
    subgraph "WebSocket Server"
        DAPHNE[Daphne ASGI Server]
        CONSUMERS[WebSocket Consumers]
        GROUPS[Channel Groups]
    end
    
    subgraph "Channel Layer"
        REDIS_CHANNELS[Redis Channel Layer]
        MESSAGE_QUEUE[Message Queue]
        GROUP_MANAGEMENT[Group Management]
    end
    
    subgraph "Django Integration"
        MODELS[Django Models]
        SIGNALS[Model Signals]
        TASKS[Background Tasks]
    end
    
    BROWSER --> DAPHNE
    RECONNECT --> DAPHNE
    HEARTBEAT --> DAPHNE
    
    DAPHNE --> CONSUMERS
    CONSUMERS --> GROUPS
    
    GROUPS --> REDIS_CHANNELS
    REDIS_CHANNELS --> MESSAGE_QUEUE
    REDIS_CHANNELS --> GROUP_MANAGEMENT
    
    CONSUMERS --> MODELS
    MODELS --> SIGNALS
    SIGNALS --> TASKS
    TASKS --> MESSAGE_QUEUE
```

### WebSocket Event Types

#### Dashboard Events
```javascript
// Real-time dashboard updates
{
  "type": "dashboard.update",
  "data": {
    "personnel_count": 45,
    "available_items": 23,
    "issued_items": 12,
    "recent_transactions": [...]
  }
}

// Transaction notifications
{
  "type": "transaction.created",
  "data": {
    "id": 123,
    "personnel": "SGT Smith",
    "item": "M16-001",
    "action": "Take",
    "timestamp": "2026-02-09T10:30:00Z"
  }
}
```

#### System Alerts
```javascript
// Security alerts
{
  "type": "security.alert",
  "data": {
    "level": "warning",
    "message": "Multiple failed login attempts detected",
    "ip_address": "192.168.1.100",
    "timestamp": "2026-02-09T10:30:00Z"
  }
}

// System status updates
{
  "type": "system.status",
  "data": {
    "database": "connected",
    "redis": "connected",
    "users_online": 3
  }
}
```

### Connection Management

#### Connection Lifecycle
1. **Connection Establishment**: WebSocket handshake with authentication
2. **Group Assignment**: User joined to relevant channel groups
3. **Heartbeat Monitoring**: Periodic ping/pong for connection health
4. **Message Broadcasting**: Real-time event distribution
5. **Graceful Disconnection**: Clean connection termination

#### Connection Security
```python
# WebSocket authentication middleware
class WebSocketAuthMiddleware:
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        # Authenticate WebSocket connection
        user = await self.authenticate_websocket(scope)
        if user:
            scope['user'] = user
            return await self.app(scope, receive, send)
        else:
            await send({'type': 'websocket.close', 'code': 4001})
```

## Security Architecture

### Multi-Layer Security Model

```mermaid
graph TB
    subgraph "Network Security Layer"
        FIREWALL[Network Firewall]
        LAN_CONTROL[LAN Access Control]
        VPN[VPN Integration]
        MAC_FILTER[MAC Address Filtering]
    end
    
    subgraph "Application Security Layer"
        HTTPS[HTTPS/SSL Encryption]
        CSP[Content Security Policy]
        CSRF[CSRF Protection]
        HEADERS[Security Headers]
    end
    
    subgraph "Authentication & Authorization"
        AUTH[User Authentication]
        MFA[Multi-Factor Auth]
        RBAC[Role-Based Access]
        PERMISSIONS[Granular Permissions]
    end
    
    subgraph "Data Protection Layer"
        ENCRYPTION[Database Encryption]
        AUDIT[Audit Logging]
        BACKUP[Secure Backups]
        SANITIZATION[Input Sanitization]
    end
    
    subgraph "Monitoring & Response"
        IDS[Intrusion Detection]
        RATE_LIMIT[Rate Limiting]
        ALERT[Security Alerts]
        INCIDENT[Incident Response]
    end
    
    FIREWALL --> HTTPS
    LAN_CONTROL --> CSP
    VPN --> CSRF
    MAC_FILTER --> HEADERS
    
    HTTPS --> AUTH
    CSP --> MFA
    CSRF --> RBAC
    HEADERS --> PERMISSIONS
    
    AUTH --> ENCRYPTION
    MFA --> AUDIT
    RBAC --> BACKUP
    PERMISSIONS --> SANITIZATION
    
    ENCRYPTION --> IDS
    AUDIT --> RATE_LIMIT
    BACKUP --> ALERT
    SANITIZATION --> INCIDENT
```

### Security Implementation Details

#### Network-Based Access Control
```python
# LAN/WAN access control decorator
@lan_required
@user_passes_test(is_admin_or_armorer)
def qr_transaction_scanner(request):
    """QR Scanner - Admin/Armorer + LAN access only"""
    return render(request, 'transactions/qr_scanner.html')

# Network middleware implementation
class NetworkBasedAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        if self.is_lan_only_path(request.path):
            if not self.is_lan_access(request):
                return HttpResponseForbidden("LAN access required")
        
        return self.get_response(request)
```

#### Role-Based Permissions
```python
# Permission matrix
ROLE_PERMISSIONS = {
    'Admin': [
        'personnel.add', 'personnel.change', 'personnel.delete',
        'inventory.add', 'inventory.change', 'inventory.delete',
        'transactions.add', 'transactions.change', 'transactions.view',
        'admin.access', 'reports.generate'
    ],
    'Armorer': [
        'personnel.view', 'personnel.change',
        'inventory.view', 'inventory.change',
        'transactions.add', 'transactions.view',
        'qr.scan', 'reports.view'
    ],
    'Staff': [
        'personnel.view', 'inventory.view',
        'transactions.view', 'reports.view'
    ]
}
```

## Network Architecture

### Network Deployment Topology

```mermaid
graph TB
    subgraph "External Network"
        INTERNET[Internet]
        VPN_SERVER[VPN Server]
    end
    
    subgraph "DMZ"
        NGINX_PROXY[Nginx Reverse Proxy]
        SSL_TERMINATION[SSL Termination]
    end
    
    subgraph "Secure LAN"
        APP_SERVER[Application Server]
        DB_SERVER[Database Server]
        REDIS_SERVER[Redis Server]
    end
    
    subgraph "Client Networks"
        LAN_CLIENTS[LAN Clients<br/>Full Access]
        VPN_CLIENTS[VPN Clients<br/>Limited Access]
        WAN_CLIENTS[WAN Clients<br/>Read-Only]
    end
    
    INTERNET --> VPN_SERVER
    VPN_SERVER --> VPN_CLIENTS
    INTERNET --> WAN_CLIENTS
    
    LAN_CLIENTS --> NGINX_PROXY
    VPN_CLIENTS --> NGINX_PROXY  
    WAN_CLIENTS --> NGINX_PROXY
    
    NGINX_PROXY --> SSL_TERMINATION
    SSL_TERMINATION --> APP_SERVER
    
    APP_SERVER --> DB_SERVER
    APP_SERVER --> REDIS_SERVER
```

### Network Security Zones

#### Zone Configuration
```yaml
# Network security zones
zones:
  secure_lan:
    ip_ranges:
      - "192.168.1.0/24"
      - "10.0.0.0/24"
    access_level: "full"
    allowed_operations:
      - "create_personnel"
      - "create_inventory"
      - "create_transactions"
      - "admin_access"
  
  vpn_network:
    ip_ranges:
      - "10.8.0.0/24"
    access_level: "limited"
    allowed_operations:
      - "view_inventory"
      - "view_personnel"
      - "view_transactions"
  
  wan_access:
    ip_ranges:
      - "0.0.0.0/0"
    access_level: "readonly"
    allowed_operations:
      - "view_status"
      - "view_reports"
```

#### Port Configuration
```bash
# Firewall rules
# LAN access (full functionality)
iptables -A INPUT -s 192.168.1.0/24 -p tcp --dport 8443 -j ACCEPT

# WAN access (limited functionality)  
iptables -A INPUT -p tcp --dport 443 -j ACCEPT

# VPN access
iptables -A INPUT -s 10.8.0.0/24 -p tcp --dport 8443 -j ACCEPT

# Internal services (database, redis)
iptables -A INPUT -s 127.0.0.1 -p tcp --dport 5432 -j ACCEPT
iptables -A INPUT -s 127.0.0.1 -p tcp --dport 6379 -j ACCEPT
```

## Deployment Architecture

### Production Deployment Pattern

```mermaid
graph TB
    subgraph "Load Balancer Tier"
        LB[Load Balancer]
        HEALTH[Health Checks]
    end
    
    subgraph "Web Server Tier"
        NGINX1[Nginx Server 1]
        NGINX2[Nginx Server 2]
    end
    
    subgraph "Application Tier"
        APP1[Django App 1]
        APP2[Django App 2]
        WEBSOCKET1[WebSocket Server 1]
        WEBSOCKET2[WebSocket Server 2]
    end
    
    subgraph "Data Tier"
        POSTGRES_PRIMARY[(PostgreSQL Primary)]
        POSTGRES_REPLICA[(PostgreSQL Replica)]
        REDIS_CLUSTER[(Redis Cluster)]
    end
    
    subgraph "Storage Tier"
        NFS[Shared File Storage]
        BACKUP[Backup Storage]
    end
    
    LB --> NGINX1
    LB --> NGINX2
    HEALTH --> LB
    
    NGINX1 --> APP1
    NGINX1 --> WEBSOCKET1
    NGINX2 --> APP2
    NGINX2 --> WEBSOCKET2
    
    APP1 --> POSTGRES_PRIMARY
    APP2 --> POSTGRES_PRIMARY
    APP1 --> REDIS_CLUSTER
    APP2 --> REDIS_CLUSTER
    
    POSTGRES_PRIMARY --> POSTGRES_REPLICA
    APP1 --> NFS
    APP2 --> NFS
    
    POSTGRES_PRIMARY --> BACKUP
    NFS --> BACKUP
```

### Containerized Deployment (Docker)

```yaml
# docker-compose.yml
version: '3.8'

services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
      - static_files:/var/www/static

  django:
    build: .
    depends_on:
      - postgres
      - redis
    environment:
      - DJANGO_SETTINGS_MODULE=core.settings_production
    volumes:
      - media_files:/app/media
      - static_files:/app/static

  websocket:
    build: .
    command: daphne -b 0.0.0.0 -p 8001 core.asgi:application
    depends_on:
      - redis

  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: armguard
      POSTGRES_USER: armguard_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
  media_files:
  static_files:
```

## Scalability Considerations

### Horizontal Scaling Architecture

```mermaid
graph TB
    subgraph "Auto Scaling Group"
        APP1[Django Instance 1]
        APP2[Django Instance 2]
        APP3[Django Instance N...]
    end
    
    subgraph "Database Scaling"
        MASTER[(PostgreSQL Master)]
        SLAVE1[(PostgreSQL Replica 1)]
        SLAVE2[(PostgreSQL Replica 2)]
    end
    
    subgraph "Cache Scaling"
        REDIS1[(Redis Cluster Node 1)]
        REDIS2[(Redis Cluster Node 2)]
        REDIS3[(Redis Cluster Node 3)]
    end
    
    subgraph "Storage Scaling"
        CDN[Content Delivery Network]
        S3[Object Storage]
        NFS[Network File System]
    end
    
    APP1 --> MASTER
    APP2 --> MASTER
    APP3 --> MASTER
    
    APP1 --> SLAVE1
    APP2 --> SLAVE2
    APP3 --> SLAVE1
    
    APP1 --> REDIS1
    APP2 --> REDIS2
    APP3 --> REDIS3
    
    MASTER --> SLAVE1
    MASTER --> SLAVE2
    
    APP1 --> CDN
    APP2 --> S3
    APP3 --> NFS
```

### Performance Optimization Strategies

#### Database Optimization
1. **Read Replicas**: Distribute read operations across multiple replicas
2. **Connection Pooling**: Reuse database connections efficiently
3. **Query Optimization**: Implement select_related and prefetch_related
4. **Index Strategy**: Strategic indexing for common query patterns
5. **Partitioning**: Date-based partitioning for large transaction tables

#### Caching Strategy
1. **Multi-Level Caching**: Template, query, and object caching
2. **Redis Clustering**: Distributed cache across multiple nodes
3. **Cache Invalidation**: Smart cache invalidation strategies
4. **Edge Caching**: CDN for static assets and media files

#### Application Optimization
1. **Code Profiling**: Regular performance monitoring and profiling
2. **Async Processing**: Background tasks for heavy operations
3. **Resource Pooling**: Connection and thread pool management
4. **Memory Management**: Efficient memory usage patterns

## Performance Architecture

### Performance Monitoring Stack

```mermaid
graph TB
    subgraph "Application Metrics"
        APM[Application Performance Monitoring]
        DJANGO_METRICS[Django Metrics]
        CUSTOM_METRICS[Custom Metrics]
    end
    
    subgraph "Infrastructure Metrics"
        SYSTEM_METRICS[System Metrics]
        DATABASE_METRICS[Database Metrics]
        CACHE_METRICS[Cache Metrics]
        NETWORK_METRICS[Network Metrics]
    end
    
    subgraph "Monitoring Tools"
        PROMETHEUS[Prometheus]
        GRAFANA[Grafana Dashboards]
        ALERTS[Alert Manager]
    end
    
    subgraph "Log Aggregation"
        LOG_COLLECTION[Log Collection]
        LOG_ANALYSIS[Log Analysis]
        LOG_ALERTS[Log-based Alerts]
    end
    
    APM --> PROMETHEUS
    DJANGO_METRICS --> PROMETHEUS
    CUSTOM_METRICS --> PROMETHEUS
    
    SYSTEM_METRICS --> PROMETHEUS
    DATABASE_METRICS --> PROMETHEUS
    CACHE_METRICS --> PROMETHEUS
    NETWORK_METRICS --> PROMETHEUS
    
    PROMETHEUS --> GRAFANA
    PROMETHEUS --> ALERTS
    
    LOG_COLLECTION --> LOG_ANALYSIS
    LOG_ANALYSIS --> LOG_ALERTS
```

### Performance Benchmarks

#### Response Time Targets
- **Page Load Time**: < 2 seconds (LAN), < 5 seconds (WAN)
- **API Response Time**: < 500ms for GET requests, < 1s for POST requests
- **WebSocket Latency**: < 100ms for real-time updates
- **Database Query Time**: < 100ms for 95% of queries

#### Scalability Targets
- **Concurrent Users**: 100+ simultaneous users (LAN deployment)
- **Transaction Volume**: 1000+ transactions per day
- **Database Records**: 10,000+ personnel records, 50,000+ transactions
- **File Storage**: 10GB+ for QR codes, photos, and documents

#### Resource Utilization Targets
- **CPU Utilization**: < 70% average, < 90% peak
- **Memory Usage**: < 80% of available RAM
- **Database Connections**: < 50% of max connections
- **Cache Hit Ratio**: > 90% for frequently accessed data

---

**Document Version**: 1.0  
**Last Updated**: February 2026  
**Next Review**: March 2026  

---

*For installation procedures, see [installation.md](installation.md)*  
*For database schema details, see [database.md](database.md)*  
*For API documentation, see [api.md](api.md)*  
*For security implementation, see [security.md](security.md)*