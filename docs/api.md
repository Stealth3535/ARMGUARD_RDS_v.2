# ARMGUARD - API Documentation

## Table of Contents
- [API Overview](#api-overview)
- [Authentication Methods](#authentication-methods)
- [API Endpoints](#api-endpoints)
- [Request/Response Format](#requestresponse-format)
- [Error Codes and Handling](#error-codes-and-handling)
- [Rate Limiting](#rate-limiting)
- [Usage Guidelines](#usage-guidelines)
- [Code Examples](#code-examples)
- [WebSocket API](#websocket-api)
- [Testing the API](#testing-the-api)

## API Overview

### API Architecture
ARMGUARD provides both **RESTful HTTP APIs** and **WebSocket APIs** for real-time communication:
- **REST API**: Standard CRUD operations for resources
- **WebSocket API**: Real-time updates and notifications
- **AJAX API**: Internal frontend communication
- **QR Scanner API**: Specialized QR code processing

### API Versions
- **Current Version**: v1.0
- **Base URL**: `https://your-domain.com/api/`
- **WebSocket URL**: `wss://your-domain.com/ws/`

### Supported Formats
- **Request**: JSON, form-data (file uploads)
- **Response**: JSON (standard), PDF (reports)
- **Content-Type**: `application/json`, `multipart/form-data`

## Authentication Methods

### Session Authentication
Primary authentication method using Django's session framework:

```python
# Login example
POST /api/auth/login/
{
    "username": "admin",
    "password": "secure_password"
}

# Response
{
    "success": true,
    "data": {
        "user_id": 1,
        "username": "admin",
        "role": "Admin",
        "session_id": "abc123..."
    }
}
```

### CSRF Protection
All POST, PUT, DELETE requests require CSRF token:

```javascript
// Get CSRF token
const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

// Include in requests
fetch('/api/personnel/', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
    },
    body: JSON.stringify(data)
});
```

### Network-based Access Control
API access restricted based on network location:

- **LAN Access**: Full CRUD operations
- **WAN Access**: Read-only operations  
- **VPN Access**: Limited operations based on role

```python
# Decorator for LAN-only endpoints
@lan_required
@user_passes_test(is_admin_or_armorer)
def create_personnel(request):
    """Personnel creation requires LAN access"""
    pass
```

## API Endpoints

### Personnel Management API

#### List Personnel
```http
GET /api/personnel/
```

**Query Parameters:**
- `page`: Page number (default: 1)
- `per_page`: Items per page (default: 25, max: 100)
- `search`: Search term (name, rank, serial)
- `rank`: Filter by rank
- `status`: Filter by status (Active, Inactive, Transferred)
- `group`: Filter by military group
- `classification`: Filter by classification (OFFICER, ENLISTED PERSONNEL)

**Example Request:**
```bash
curl -X GET "https://your-domain.com/api/personnel/?page=1&rank=SGT&status=Active" \
     -H "Cookie: sessionid=abc123..."
```

**Example Response:**
```json
{
    "success": true,
    "data": [
        {
            "id": "PE-12345678-090226",
            "surname": "Smith",
            "firstname": "John",
            "middle_initial": "A",
            "rank": "SGT",
            "serial": "12345678",
            "group": "HAS",
            "classification": "ENLISTED PERSONNEL",
            "status": "Active",
            "telephone": "+63-123-456-7890",
            "picture": "/media/personnel/photos/PE-12345678-090226.jpg",
            "qr_code": "PERSONNEL:PE-12345678-090226",
            "created_at": "2026-02-09T10:30:00Z",
            "updated_at": "2026-02-09T10:30:00Z"
        }
    ],
    "pagination": {
        "page": 1,
        "per_page": 25,
        "total_pages": 3,
        "total_count": 67,
        "has_next": true,
        "has_prev": false
    }
}
```

#### Create Personnel
```http
POST /api/personnel/
```

**Request Body:**
```json
{
    "surname": "Johnson",
    "firstname": "Alice",
    "middle_initial": "B",
    "rank": "CPL",
    "serial": "87654321",
    "group": "HAS",
    "classification": "ENLISTED PERSONNEL",
    "telephone": "+63-987-654-3210",
    "picture": "base64_encoded_image_data"
}
```

**Response:**
```json
{
    "success": true,
    "data": {
        "id": "PE-87654321-090226",
        "surname": "Johnson",
        "firstname": "Alice",
        "rank": "CPL",
        "serial": "87654321",
        "status": "Active",
        "created_at": "2026-02-09T11:00:00Z"
    },
    "message": "Personnel created successfully"
}
```

#### Get Personnel Details
```http
GET /api/personnel/{id}/
```

**Example:**
```bash
curl -X GET "https://your-domain.com/api/personnel/PE-12345678-090226/" \
     -H "Cookie: sessionid=abc123..."
```

#### Update Personnel
```http
PUT /api/personnel/{id}/
PATCH /api/personnel/{id}/
```

**PATCH Example (Partial Update):**
```json
{
    "telephone": "+63-111-222-3333",
    "status": "Transferred"
}
```

#### Delete Personnel (Soft Delete)
```http
DELETE /api/personnel/{id}/
```

**Response:**
```json
{
    "success": true,
    "message": "Personnel record deleted successfully",
    "data": {
        "id": "PE-12345678-090226",
        "deleted_at": "2026-02-09T12:00:00Z"
    }
}
```

### Inventory Management API

#### List Inventory Items
```http
GET /api/inventory/
```

**Query Parameters:**
- `item_type`: Filter by weapon type (M14, M16, M4, GLOCK, 45)
- `status`: Filter by status (Available, Issued, Maintenance, Retired)
- `condition`: Filter by condition (Good, Fair, Poor, Damaged)
- `search`: Search by serial number or description

**Example Response:**
```json
{
    "success": true,
    "data": [
        {
            "id": "IR-M16001-090226",
            "item_type": "M16",
            "serial": "M16001",
            "description": "Standard M16A4 Rifle",
            "condition": "Good",
            "status": "Available",
            "registration_date": "2026-02-09",
            "qr_code": "ITEM:IR-M16001-090226",
            "created_at": "2026-02-09T09:00:00Z"
        }
    ]
}
```

#### Create Inventory Item
```http
POST /api/inventory/
```

**Request Body:**
```json
{
    "item_type": "M16",
    "serial": "M16002",
    "description": "M16A4 Rifle - Excellent Condition",
    "condition": "Good"
}
```

#### Update Item Status
```http
PATCH /api/inventory/{id}/status/
```

**Request Body:**
```json
{
    "status": "Maintenance",
    "reason": "Routine cleaning and inspection"
}
```

### Transaction Processing API

#### List Transactions
```http
GET /api/transactions/
```

**Query Parameters:**
- `personnel_id`: Filter by personnel
- `item_id`: Filter by item
- `action`: Filter by action (Take, Return)
- `date_from`: Filter from date (YYYY-MM-DD)
- `date_to`: Filter to date (YYYY-MM-DD)

**Example Response:**
```json
{
    "success": true,
    "data": [
        {
            "id": 123,
            "personnel": {
                "id": "PE-12345678-090226",
                "name": "SGT John Smith",
                "rank": "SGT"
            },
            "item": {
                "id": "IR-M16001-090226",
                "type": "M16",
                "serial": "M16001"
            },
            "action": "Take",
            "date_time": "2026-02-09T10:30:00Z",
            "mags": 3,
            "rounds": 90,
            "duty_type": "Training Exercise",
            "notes": "Authorization: CO-2026-001",
            "issued_by": {
                "id": 1,
                "username": "armorer01",
                "name": "CPL Jane Doe"
            }
        }
    ]
}
```

#### Create Transaction
```http
POST /api/transactions/
```

**Request Body:**
```json
{
    "personnel_id": "PE-12345678-090226",
    "item_id": "IR-M16001-090226",
    "action": "Take",
    "mags": 3,
    "rounds": 90,
    "duty_type": "Training Exercise",
    "notes": "Authorization: CO-2026-001"
}
```

#### QR-based Transaction
```http
POST /api/transactions/qr/
```

**Request Body:**
```json
{
    "personnel_qr": "PERSONNEL:PE-12345678-090226",
    "item_qr": "ITEM:IR-M16001-090226",
    "action": "Take",
    "mags": 2,
    "rounds": 60,
    "duty_type": "Guard Duty"
}
```

#### Process Return
```http
POST /api/transactions/return/
```

**Request Body:**
```json
{
    "item_id": "IR-M16001-090226",
    "notes": "Weapon returned in good condition"
}
```

### QR Code Management API

#### Generate QR Code
```http
POST /api/qr/generate/
```

**Request Body:**
```json
{
    "qr_type": "Personnel",
    "reference_id": "PE-12345678-090226"
}
```

**Response:**
```json
{
    "success": true,
    "data": {
        "qr_data": "PERSONNEL:PE-12345678-090226",
        "qr_image_url": "/media/qr_codes/personnel/PE-12345678-090226.png",
        "qr_image_base64": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA..."
    }
}
```

#### Scan QR Code
```http
POST /api/qr/scan/
```

**Request Body:**
```json
{
    "qr_data": "PERSONNEL:PE-12345678-090226"
}
```

**Response:**
```json
{
    "success": true,
    "data": {
        "type": "Personnel",
        "reference_id": "PE-12345678-090226",
        "details": {
            "id": "PE-12345678-090226",
            "name": "SGT John Smith",
            "rank": "SGT",
            "status": "Active"
        }
    }
}
```

### Authentication API

#### Login
```http
POST /api/auth/login/
```

**Request Body:**
```json
{
    "username": "admin",
    "password": "secure_password"
}
```

#### Logout
```http
POST /api/auth/logout/
```

#### Get Current User
```http
GET /api/auth/user/
```

**Response:**
```json
{
    "success": true,
    "data": {
        "id": 1,
        "username": "admin",
        "first_name": "Admin",
        "last_name": "User",
        "email": "admin@armguard.com",
        "role": "Admin",
        "is_staff": true,
        "is_superuser": true,
        "last_login": "2026-02-09T09:00:00Z"
    }
}
```

### Reporting API

#### Transaction Report
```http
GET /api/reports/transactions/
```

**Query Parameters:**
- `format`: Response format (json, pdf, csv)
- `date_from`: Start date
- `date_to`: End date
- `personnel_id`: Filter by personnel
- `item_type`: Filter by item type

**Example:**
```bash
curl -X GET "https://your-domain.com/api/reports/transactions/?format=pdf&date_from=2026-02-01&date_to=2026-02-09" \
     -H "Cookie: sessionid=abc123..." \
     --output transaction_report.pdf
```

#### Inventory Status Report
```http
GET /api/reports/inventory/
```

**Response:**
```json
{
    "success": true,
    "data": {
        "summary": {
            "total_items": 45,
            "available": 23,
            "issued": 18,
            "maintenance": 3,
            "retired": 1
        },
        "by_type": {
            "M16": {"total": 15, "available": 8, "issued": 6, "maintenance": 1},
            "M4": {"total": 12, "available": 7, "issued": 5, "maintenance": 0},
            "GLOCK": {"total": 10, "available": 5, "issued": 4, "maintenance": 1},
            "45": {"total": 8, "available": 3, "issued": 3, "maintenance": 1, "retired": 1}
        }
    }
}
```

## Request/Response Format

### Standard Request Headers
```http
Content-Type: application/json
X-CSRFToken: csrf_token_here
Cookie: sessionid=session_id_here
User-Agent: ArmGuard-Client/1.0
```

### Standard Response Format

#### Success Response
```json
{
    "success": true,
    "data": {
        // Response data
    },
    "message": "Operation completed successfully",
    "meta": {
        "timestamp": "2026-02-09T10:30:00Z",
        "version": "1.0",
        "request_id": "req_123456789"
    }
}
```

#### Error Response
```json
{
    "success": false,
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "Invalid data provided",
        "details": {
            "field_name": ["Error message for this field"],
            "another_field": ["Another error message"]
        }
    },
    "meta": {
        "timestamp": "2026-02-09T10:30:00Z",
        "version": "1.0",
        "request_id": "req_123456789"
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
        "has_prev": false,
        "next_url": "/api/personnel/?page=2",
        "prev_url": null
    }
}
```

## Error Codes and Handling

### HTTP Status Codes
- `200 OK`: Request successful
- `201 Created`: Resource created successfully
- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Access denied
- `404 Not Found`: Resource not found
- `409 Conflict`: Resource conflict (e.g., duplicate serial)
- `422 Unprocessable Entity`: Validation errors
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error

### Custom Error Codes
```json
{
    "error": {
        "code": "PERSONNEL_NOT_FOUND",
        "message": "Personnel record not found",
        "details": {
            "personnel_id": "PE-12345678-090226"
        }
    }
}
```

#### Personnel API Errors
- `PERSONNEL_NOT_FOUND`: Personnel record doesn't exist
- `DUPLICATE_SERIAL`: Serial number already in use
- `INVALID_RANK`: Invalid military rank provided
- `PERSONNEL_HAS_TRANSACTIONS`: Cannot delete personnel with transaction history

#### Inventory API Errors
- `ITEM_NOT_FOUND`: Inventory item doesn't exist
- `DUPLICATE_ITEM_SERIAL`: Item serial already exists
- `INVALID_ITEM_TYPE`: Invalid weapon type
- `ITEM_NOT_AVAILABLE`: Item cannot be issued (not available)
- `ITEM_ALREADY_ISSUED`: Item is already issued to someone

#### Transaction API Errors
- `INVALID_TRANSACTION_ACTION`: Invalid action (must be Take or Return)
- `PERSONNEL_INACTIVE`: Personnel is not active
- `ITEM_STATUS_CONFLICT`: Item status conflicts with action
- `OUTSTANDING_ITEMS_LIMIT`: Personnel has reached maximum issued items
- `RETURN_VALIDATION_FAILED`: Cannot return item that wasn't issued to this personnel

#### QR Code API Errors
- `INVALID_QR_DATA`: QR code data format is invalid
- `QR_REFERENCE_NOT_FOUND`: Referenced personnel/item not found
- `QR_GENERATION_FAILED`: Failed to generate QR code image

### Error Handling Examples

```javascript
// JavaScript error handling
async function createPersonnel(personnelData) {
    try {
        const response = await fetch('/api/personnel/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify(personnelData)
        });
        
        const data = await response.json();
        
        if (!data.success) {
            // Handle specific errors
            switch (data.error.code) {
                case 'DUPLICATE_SERIAL':
                    showError('Serial number is already in use');
                    break;
                case 'INVALID_RANK':
                    showError('Please select a valid military rank');
                    break;
                case 'VALIDATION_ERROR':
                    showValidationErrors(data.error.details);
                    break;
                default:
                    showError(data.error.message);
            }
            return null;
        }
        
        return data.data;
        
    } catch (error) {
        console.error('Network error:', error);
        showError('Network error. Please try again.');
        return null;
    }
}
```

```python
# Python error handling
import requests

def get_personnel(personnel_id, session_id):
    try:
        response = requests.get(
            f'https://your-domain.com/api/personnel/{personnel_id}/',
            cookies={'sessionid': session_id}
        )
        
        data = response.json()
        
        if not data['success']:
            error_code = data['error']['code']
            print(f"API Error: {error_code} - {data['error']['message']}")
            return None
            
        return data['data']
        
    except requests.exceptions.RequestException as e:
        print(f"Network error: {e}")
        return None
    except ValueError as e:
        print(f"JSON parsing error: {e}")
        return None
```

## Rate Limiting

### Rate Limiting Rules
- **Default Limit**: 60 requests per minute per IP address
- **Authenticated Users**: 120 requests per minute
- **Admin Users**: 300 requests per minute
- **Burst Limit**: 10 requests per 10-second window

### Rate Limiting Headers
Response headers indicate current rate limit status:
```http
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1644404400
X-RateLimit-Retry-After: 30
```

### Rate Limiting Response
When rate limit is exceeded:
```json
{
    "success": false,
    "error": {
        "code": "RATE_LIMIT_EXCEEDED",
        "message": "Too many requests. Please try again later.",
        "details": {
            "limit": 60,
            "window": 60,
            "retry_after": 30
        }
    }
}
```

### Rate Limiting Best Practices
1. **Implement Exponential Backoff**: Gradually increase retry delays
2. **Cache Responses**: Store frequently accessed data locally
3. **Batch Requests**: Combine multiple operations when possible
4. **Use WebSockets**: For real-time updates instead of polling

## Usage Guidelines

### API Best Practices

#### 1. Authentication and Security
```javascript
// Always include CSRF token for write operations
const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

// Use HTTPS in production
const baseUrl = 'https://your-domain.com/api/';

// Handle session expiration
if (response.status === 401) {
    window.location.href = '/login/';
}
```

#### 2. Error Handling
```javascript
// Comprehensive error handling
async function apiRequest(url, options = {}) {
    try {
        const response = await fetch(url, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken(),
                ...options.headers
            }
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${data.error?.message || 'Unknown error'}`);
        }
        
        if (!data.success) {
            throw new Error(data.error.message);
        }
        
        return data.data;
        
    } catch (error) {
        console.error('API request failed:', error);
        throw error;
    }
}
```

#### 3. Pagination Handling
```javascript
// Handle paginated responses
async function getAllPersonnel() {
    let allPersonnel = [];
    let page = 1;
    let hasMore = true;
    
    while (hasMore) {
        const response = await fetch(`/api/personnel/?page=${page}`);
        const data = await response.json();
        
        allPersonnel = allPersonnel.concat(data.data);
        hasMore = data.pagination.has_next;
        page++;
    }
    
    return allPersonnel;
}
```

#### 4. Caching Strategy
```javascript
// Simple cache implementation
class APICache {
    constructor(ttl = 300000) { // 5 minutes TTL
        this.cache = new Map();
        this.ttl = ttl;
    }
    
    get(key) {
        const item = this.cache.get(key);
        if (!item) return null;
        
        if (Date.now() - item.timestamp > this.ttl) {
            this.cache.delete(key);
            return null;
        }
        
        return item.data;
    }
    
    set(key, data) {
        this.cache.set(key, {
            data: data,
            timestamp: Date.now()
        });
    }
}

const apiCache = new APICache();

// Use cache in API calls
async function getPersonnelWithCache(id) {
    const cacheKey = `personnel:${id}`;
    let personnel = apiCache.get(cacheKey);
    
    if (!personnel) {
        personnel = await apiRequest(`/api/personnel/${id}/`);
        apiCache.set(cacheKey, personnel);
    }
    
    return personnel;
}
```

### Network Access Considerations

#### LAN vs WAN Operations
```javascript
// Check network context before operations
async function createTransaction(transactionData) {
    // Transaction creation requires LAN access
    const networkInfo = await fetch('/api/network-info/').then(r => r.json());
    
    if (!networkInfo.is_lan_access) {
        throw new Error('Transaction creation requires LAN access');
    }
    
    return await apiRequest('/api/transactions/', {
        method: 'POST',
        body: JSON.stringify(transactionData)
    });
}
```

#### Offline Handling
```javascript
// Basic offline support
class OfflineQueue {
    constructor() {
        this.queue = JSON.parse(localStorage.getItem('offline_queue') || '[]');
    }
    
    add(request) {
        this.queue.push({
            ...request,
            timestamp: Date.now(),
            id: Math.random().toString(36)
        });
        this.save();
    }
    
    save() {
        localStorage.setItem('offline_queue', JSON.stringify(this.queue));
    }
    
    async processQueue() {
        const queue = [...this.queue];
        this.queue = [];
        this.save();
        
        for (const request of queue) {
            try {
                await fetch(request.url, request.options);
            } catch (error) {
                // Re-queue failed requests
                this.add(request);
            }
        }
    }
}

const offlineQueue = new OfflineQueue();

// Check online status and process queue
window.addEventListener('online', () => {
    offlineQueue.processQueue();
});
```

## Code Examples

### Complete Personnel Management Example

```html
<!DOCTYPE html>
<html>
<head>
    <title>Personnel Management</title>
</head>
<body>
    <!-- Personnel Form -->
    <form id="personnel-form">
        {% csrf_token %}
        <input type="text" id="surname" placeholder="Surname" required>
        <input type="text" id="firstname" placeholder="First Name" required>
        <select id="rank" required>
            <option value="SGT">Sergeant</option>
            <option value="CPL">Corporal</option>
            <option value="PVT">Private</option>
        </select>
        <input type="text" id="serial" placeholder="Serial Number" required>
        <button type="submit">Create Personnel</button>
    </form>
    
    <!-- Personnel List -->
    <div id="personnel-list"></div>
    
    <script>
        class PersonnelManager {
            constructor() {
                this.baseUrl = '/api/personnel/';
                this.csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
            }
            
            async createPersonnel(data) {
                try {
                    const response = await fetch(this.baseUrl, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': this.csrfToken
                        },
                        body: JSON.stringify(data)
                    });
                    
                    const result = await response.json();
                    
                    if (!result.success) {
                        this.showError(result.error.message);
                        return null;
                    }
                    
                    this.showSuccess('Personnel created successfully');
                    return result.data;
                    
                } catch (error) {
                    this.showError('Network error occurred');
                    return null;
                }
            }
            
            async loadPersonnel() {
                try {
                    const response = await fetch(this.baseUrl);
                    const result = await response.json();
                    
                    if (result.success) {
                        this.renderPersonnelList(result.data);
                    }
                } catch (error) {
                    this.showError('Failed to load personnel');
                }
            }
            
            renderPersonnelList(personnel) {
                const listContainer = document.getElementById('personnel-list');
                listContainer.innerHTML = personnel.map(p => `
                    <div class="personnel-item">
                        <h3>${p.rank} ${p.firstname} ${p.surname}</h3>
                        <p>Serial: ${p.serial}</p>
                        <p>Status: ${p.status}</p>
                        <button onclick="personnelManager.deletePersonnel('${p.id}')">
                            Delete
                        </button>
                    </div>
                `).join('');
            }
            
            async deletePersonnel(id) {
                if (!confirm('Are you sure?')) return;
                
                try {
                    const response = await fetch(`${this.baseUrl}${id}/`, {
                        method: 'DELETE',
                        headers: {
                            'X-CSRFToken': this.csrfToken
                        }
                    });
                    
                    const result = await response.json();
                    
                    if (result.success) {
                        this.showSuccess('Personnel deleted');
                        this.loadPersonnel(); // Refresh list
                    } else {
                        this.showError(result.error.message);
                    }
                } catch (error) {
                    this.showError('Failed to delete personnel');
                }
            }
            
            showSuccess(message) {
                alert(`Success: ${message}`);
            }
            
            showError(message) {
                alert(`Error: ${message}`);
            }
        }
        
        const personnelManager = new PersonnelManager();
        
        // Handle form submission
        document.getElementById('personnel-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const formData = {
                surname: document.getElementById('surname').value,
                firstname: document.getElementById('firstname').value,
                rank: document.getElementById('rank').value,
                serial: document.getElementById('serial').value
            };
            
            const result = await personnelManager.createPersonnel(formData);
            if (result) {
                e.target.reset();
                personnelManager.loadPersonnel();
            }
        });
        
        // Load initial data
        personnelManager.loadPersonnel();
    </script>
</body>
</html>
```

### QR Code Integration Example

```javascript
class QRScanner {
    constructor() {
        this.isScanning = false;
        this.video = null;
        this.stream = null;
    }
    
    async startScanning(callback) {
        if (this.isScanning) return;
        
        try {
            this.stream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: 'environment' }
            });
            
            this.video = document.createElement('video');
            this.video.srcObject = this.stream;
            this.video.play();
            
            this.isScanning = true;
            this.scanLoop(callback);
            
        } catch (error) {
            console.error('Failed to start camera:', error);
            throw error;
        }
    }
    
    scanLoop(callback) {
        if (!this.isScanning) return;
        
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        
        canvas.width = this.video.videoWidth;
        canvas.height = this.video.videoHeight;
        
        ctx.drawImage(this.video, 0, 0);
        
        // Use a QR code library like jsQR
        const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
        const qrResult = jsQR(imageData.data, canvas.width, canvas.height);
        
        if (qrResult) {
            this.stopScanning();
            callback(qrResult.data);
        } else {
            requestAnimationFrame(() => this.scanLoop(callback));
        }
    }
    
    stopScanning() {
        this.isScanning = false;
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
        }
    }
    
    async processQRCode(qrData) {
        try {
            const response = await fetch('/api/qr/scan/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                },
                body: JSON.stringify({ qr_data: qrData })
            });
            
            const result = await response.json();
            
            if (result.success) {
                return result.data;
            } else {
                throw new Error(result.error.message);
            }
        } catch (error) {
            console.error('QR processing failed:', error);
            throw error;
        }
    }
}

// Usage example
const qrScanner = new QRScanner();

document.getElementById('scan-btn').addEventListener('click', async () => {
    try {
        await qrScanner.startScanning(async (qrData) => {
            try {
                const result = await qrScanner.processQRCode(qrData);
                console.log('QR scan result:', result);
                
                // Handle different QR types
                if (result.type === 'Personnel') {
                    showPersonnelDetails(result.details);
                } else if (result.type === 'Item') {
                    showItemDetails(result.details);
                }
            } catch (error) {
                alert(`QR scan error: ${error.message}`);
            }
        });
    } catch (error) {
        alert(`Camera error: ${error.message}`);
    }
});
```

## WebSocket API

### Connection Establishment
```javascript
// Connect to WebSocket
const wsUrl = `wss://${window.location.host}/ws/dashboard/`;
const socket = new WebSocket(wsUrl);

socket.onopen = function(e) {
    console.log('WebSocket connected');
    
    // Send authentication if required
    socket.send(JSON.stringify({
        type: 'authentication',
        token: getAuthToken()
    }));
};

socket.onclose = function(e) {
    console.log('WebSocket disconnected');
    // Implement reconnection logic
    setTimeout(connectWebSocket, 5000);
};

socket.onerror = function(error) {
    console.error('WebSocket error:', error);
};
```

### Real-time Updates
```javascript
socket.onmessage = function(e) {
    const data = JSON.parse(e.data);
    
    switch (data.type) {
        case 'dashboard.update':
            updateDashboard(data.data);
            break;
            
        case 'transaction.created':
            showTransactionNotification(data.data);
            break;
            
        case 'system.alert':
            showSystemAlert(data.data);
            break;
            
        case 'user.notification':
            showUserNotification(data.data);
            break;
    }
};

// Send WebSocket message
function sendWebSocketMessage(type, data) {
    if (socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({
            type: type,
            data: data
        }));
    }
}
```

### WebSocket Event Types

#### Dashboard Updates
```json
{
    "type": "dashboard.update",
    "data": {
        "personnel_count": 45,
        "available_items": 23,
        "issued_items": 12,
        "recent_transactions": [
            {
                "id": 123,
                "personnel": "SGT Smith",
                "item": "M16-001",
                "action": "Take"
            }
        ]
    }
}
```

#### Transaction Notifications
```json
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

## Testing the API

### Manual Testing with cURL

#### Test Authentication
```bash
# Login
curl -X POST https://your-domain.com/api/auth/login/ \
     -H "Content-Type: application/json" \
     -d '{"username":"admin","password":"password"}' \
     -c cookies.txt

# Use session for subsequent requests
curl -X GET https://your-domain.com/api/personnel/ \
     -b cookies.txt
```

#### Test Personnel API
```bash
# Create personnel
curl -X POST https://your-domain.com/api/personnel/ \
     -H "Content-Type: application/json" \
     -H "X-CSRFToken: your_csrf_token" \
     -b cookies.txt \
     -d '{
       "surname": "Test",
       "firstname": "User", 
       "rank": "SGT",
       "serial": "12345678"
     }'

# Get personnel list
curl -X GET https://your-domain.com/api/personnel/?page=1&per_page=10 \
     -b cookies.txt
```

### Automated Testing with Python

```python
import requests
import json
import unittest

class APITestCase(unittest.TestCase):
    def setUp(self):
        self.base_url = 'https://your-domain.com/api'
        self.session = requests.Session()
        
        # Login
        login_data = {
            'username': 'testuser',
            'password': 'testpassword'
        }
        response = self.session.post(f'{self.base_url}/auth/login/', json=login_data)
        self.assertEqual(response.status_code, 200)
        
        # Get CSRF token
        self.csrf_token = self.session.cookies.get('csrftoken')
        self.session.headers.update({'X-CSRFToken': self.csrf_token})
    
    def test_create_personnel(self):
        personnel_data = {
            'surname': 'TestSurname',
            'firstname': 'TestFirstname',
            'rank': 'SGT',
            'serial': '87654321'
        }
        
        response = self.session.post(f'{self.base_url}/personnel/', json=personnel_data)
        
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('id', data['data'])
        
        return data['data']['id']  # Return for cleanup
    
    def test_get_personnel_list(self):
        response = self.session.get(f'{self.base_url}/personnel/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('data', data)
        self.assertIn('pagination', data)
    
    def test_invalid_personnel_data(self):
        invalid_data = {
            'surname': '',  # Empty surname should fail
            'firstname': 'Test',
            'rank': 'INVALID_RANK',  # Invalid rank
            'serial': '123'  # Too short serial
        }
        
        response = self.session.post(f'{self.base_url}/personnel/', json=invalid_data)
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['error']['code'], 'VALIDATION_ERROR')

if __name__ == '__main__':
    unittest.main()
```

### JavaScript Unit Tests

```javascript
// API test suite using Jest
describe('ARMGUARD API', () => {
    let authToken;
    
    beforeAll(async () => {
        // Login before tests
        const response = await fetch('/api/auth/login/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                username: 'testuser',
                password: 'testpassword'
            })
        });
        
        const data = await response.json();
        expect(data.success).toBe(true);
        authToken = data.data.token;
    });
    
    describe('Personnel API', () => {
        test('should create personnel', async () => {
            const personnelData = {
                surname: 'Test',
                firstname: 'User',
                rank: 'SGT',
                serial: '12345678'
            };
            
            const response = await fetch('/api/personnel/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${authToken}`
                },
                body: JSON.stringify(personnelData)
            });
            
            const data = await response.json();
            expect(response.status).toBe(201);
            expect(data.success).toBe(true);
            expect(data.data.surname).toBe('Test');
        });
        
        test('should list personnel with pagination', async () => {
            const response = await fetch('/api/personnel/?page=1&per_page=5', {
                headers: {
                    'Authorization': `Bearer ${authToken}`
                }
            });
            
            const data = await response.json();
            expect(response.status).toBe(200);
            expect(data.success).toBe(true);
            expect(Array.isArray(data.data)).toBe(true);
            expect(data.pagination).toBeDefined();
            expect(data.pagination.per_page).toBe(5);
        });
    });
    
    describe('QR Code API', () => {
        test('should process valid QR code', async () => {
            const qrData = {
                qr_data: 'PERSONNEL:PE-12345678-090226'
            };
            
            const response = await fetch('/api/qr/scan/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${authToken}`
                },
                body: JSON.stringify(qrData)
            });
            
            const data = await response.json();
            expect(response.status).toBe(200);
            expect(data.success).toBe(true);
            expect(data.data.type).toBe('Personnel');
        });
    });
});
```

---

**Document Version**: 1.0  
**Last Updated**: February 2026  
**Next Review**: March 2026  

---

*For authentication details, see [security.md](security.md)*  
*For database schema, see [database.md](database.md)*  
*For system architecture, see [architecture.md](architecture.md)*  
*For installation procedures, see [installation.md](installation.md)*