# ARMGUARD RDS — Device Authorization System: Security Review & Documentation

> **Prepared by:** GitHub Copilot Security Analysis  
> **Scope:** `core/middleware/device_authorization.py`, `admin/device_auth_models.py`, `admin/views.py`, `admin/models.py (DeviceAccessLog)`, `authorized_devices.json`  
> **Classification:** Internal — Security Sensitive

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Architecture](#2-system-architecture)
3. [Authorization Flow](#3-authorization-flow)
4. [Fingerprint Construction Algorithm](#4-fingerprint-construction-algorithm)
5. [Authorization Duration & Expiry](#5-authorization-duration--expiry)
6. [Security Levels](#6-security-levels)
7. [Path Protection Configuration](#7-path-protection-configuration)
8. [Lockout & Rate Limiting](#8-lockout--rate-limiting)
9. [Active Hours Enforcement](#9-active-hours-enforcement)
10. [Transaction Limits](#10-transaction-limits)
11. [Audit Trail — DeviceAccessLog](#11-audit-trail--deviceaccesslog)
12. [mTLS Support](#12-mtls-support)
13. [Pros & Strengths](#13-pros--strengths)
14. [Cons & Risks](#14-cons--risks)
15. [Bug Report: Active Hours Parsing](#15-bug-report-active-hours-parsing)
16. [Security Improvement Recommendations](#16-security-improvement-recommendations)
17. [Compliance Claims vs. Reality](#17-compliance-claims-vs-reality)

---

## 1. Executive Summary

ARMGUARD RDS uses a custom Django middleware (`DeviceAuthorizationMiddleware`) to enforce device-level access control on top of standard user authentication. Every incoming request to a protected URL is checked against a whitelist of approved devices stored in a flat JSON file (`authorized_devices.json`).

**The system provides:** device identity binding, path-tiered security enforcement, active-hours restrictions, per-device transaction limits, brute-force lockout, and a full forensic audit trail.

**Critical gaps identified:**

| Risk | Severity | Description |
|------|----------|-------------|
| No authorization expiry | HIGH | Approved devices remain authorized indefinitely |
| Cache-backed lockout/limits | HIGH | Lockouts and transaction counters are lost on server restart |
| Flat file storage | MEDIUM | Authorization data is a plain JSON file—no DB integrity |
| Active hours parsing bug | MEDIUM | `active_hours` stored as string but parsed as dict (AttributeError) |
| Fingerprint spoofability | MEDIUM | Headers in the fingerprint hash can be spoofed |
| Cookie-based identity | LOW–MEDIUM | Cookie is the device identity anchor — loss = loss of access |

---

## 2. System Architecture

```
Browser / Client
       │
       │  Cookie: armguard_device_id (UUID, 2-year max_age)
       ▼
DeviceAuthorizationMiddleware.process_request()
       │
       ├── is_restricted_path(path) ──────┐
       │         (returns False / RESTRICTED / HIGH_SECURITY)
       │                                  │
       │   [exempt: static, login, ...]   │
       │                                  ▼
       │              get_device_fingerprint(request)
       │              SHA256[:32](UA|AccLang|AccEnc|IP|cookie_id)
       │                                  │
       │              is_device_authorized(fingerprint, ip, path)
       │                   │
       │                   ├── lockout check (Django cache)
       │                   ├── allow_all bypass (DEBUG only)
       │                   ├── fingerprint lookup in authorized_devices.json
       │                   ├── IP fallback for legacy entries (no fingerprint)
       │                   ├── security level rank check
       │                   ├── active flag check
       │                   ├── IP binding check (optional per device)
       │                   ├── active_hours check (optional per device)
       │                   ├── daily transaction limit check (cache)
       │                   └── authorized_users check (optional per device)
       │
       ├── [AUTHORIZED] → log success → return None (allow)
       └── [UNAUTHORIZED] → log failure → redirect /admin/device/request-authorization/
                                          or JSON 403 for API paths
```

**Storage components:**

| Component | Storage | Persistence |
|-----------|---------|-------------|
| Approved device list | `authorized_devices.json` (filesystem) | Persistent |
| Authorization requests (workflow) | Django DB (`DeviceAuthorizationRequest`) | Persistent |
| Access audit log | Django DB (`DeviceAccessLog`) | Persistent |
| Brute-force lockout state | Django cache | **NOT persistent** (lost on restart) |
| Daily transaction counters | Django cache | **NOT persistent** (lost on restart) |
| Security alerts (dashboard) | Django cache (last 100) | **NOT persistent** |

---

## 3. Authorization Flow

### 3.1 First-Time Device Request (New Device)

```
1. User visits any protected URL on an unknown device
         │
         ▼
2. Middleware blocks request → redirects to:
   GET /admin/device/request-authorization/
         │
         ▼
3. If user is not logged in → redirected to /login/ first
         │
         ▼
4. User submits form (POST):
      - device_name  : human-readable label (e.g., "Armory PC Terminal")
      - reason       : justification text
      - csr_pem      : (optional) PEM certificate signing request for mTLS
         │
         ▼
5. View creates DeviceAuthorizationRequest in DB:
      status          = 'pending'
      device_fingerprint = SHA256[:32] of request headers + cookie
      ip_address      = client IP
      user_agent      = HTTP_USER_AGENT
      requested_by    = logged-in User
         │
         ▼
6. Admin reviews pending request at:
   /admin/device/manage-requests/
         │
         ├── APPROVE → DeviceAuthorizationRequest.approve(reviewer)
         │               Sets status = 'approved'
         │               Calls middleware.authorize_device() ──────────────────┐
         │                                                                     ▼
         │                                               Writes entry to authorized_devices.json:
         │                                               {
         │                                                 "fingerprint": "...",
         │                                                 "name": "...",
         │                                                 "ip": "...",
         │                                                 "active": true,
         │                                                 "security_level": "...",
         │                                                 "can_transact": true/false,
         │                                                 "max_daily_transactions": 50,
         │                                                 "created_at": "2026-...",
         │                                                 "authorized_by": "system"
         │                                               }
         │
         └── REJECT → Sets status = 'rejected' only (no JSON write)
```

### 3.2 Subsequent Requests (Approved Device)

```
1. Browser sends request with cookie: armguard_device_id=<uuid>
         │
         ▼
2. Middleware builds fingerprint from: UA + AccLang + AccEnc + IP + cookie
         │
         ▼
3. Looks up fingerprint in authorized_devices["devices"] list (O(n) linear scan)
         │
         ├── Found → runs all secondary checks (see §3.3)
         └── Not found → tries legacy IP-only match for old records without fingerprint
                   └── Still not found → records failed attempt → redirect to request page
```

### 3.3 Secondary Authorization Checks (in order)

| Check | Failure Reason | Action |
|-------|---------------|--------|
| Device locked out | `locked_out` | Return False |
| `allow_all` + DEBUG | `allow_all_debug` | Return True (bypass all) |
| Fingerprint match | `device_not_registered` | Record failed attempt, return False |
| Security level rank | `insufficient_security_level_*` | Return False |
| `active` flag | `device_deactivated` | Return False |
| IP binding | `ip_mismatch` | Record failed attempt, return False |
| Active hours | `outside_active_hours` | Return False |
| Transaction limit | `daily_transaction_limit_exceeded` | Return False |
| User group binding | `user_not_authorized_for_device` | Return False |

### 3.4 Cookie Attachment

The device identity cookie (`armguard_device_id`) is set when a user first visits the authorization request page:

```
max_age   = 63,072,000 seconds (2 years)
secure    = True in production (HTTPS only)
httponly  = True (JavaScript cannot read it)
samesite  = 'Lax'
```

The cookie is a UUID hex string validated against: alphanumeric + `-_`, max 64 characters.

### 3.5 Auto-Recovery Mechanisms

The system includes several automatic recovery flows for edge cases:

| Scenario | Recovery Action |
|----------|----------------|
| Approved record exists but device missing from JSON | Auto re-adds device to JSON with `HIGH_SECURITY` level |
| Device approved but security level too low for `/admin/` | Auto-upgrades to `HIGH_SECURITY` |
| New browser session / incognito (same IP + UA, no cookie) | Rotates stored fingerprint to new cookie-backed fingerprint |
| Stale approved record (not in JSON) | Archives old record, creates new pending request |

---

## 4. Fingerprint Construction Algorithm

```python
# Step 1: Collect headers
user_agent      = request.META.get('HTTP_USER_AGENT', '')
accept_language = request.META.get('HTTP_ACCEPT_LANGUAGE', '')
accept_encoding = request.META.get('HTTP_ACCEPT_ENCODING', '')
remote_addr     = client_ip  # respects X-Forwarded-For

# Step 2: Include cookie-based device ID (primary fingerprint)
device_id = cookie value of armguard_device_id

# Step 3: Concatenate
fingerprint_data = f"{user_agent}|{accept_language}|{accept_encoding}|{remote_addr}|{device_id}"

# Step 4: Hash (truncated to 32 hex chars = 128 bits)
fingerprint = hashlib.sha256(fingerprint_data.encode()).hexdigest()[:32]
```

**Legacy fingerprint** (backward compatibility):  
Same formula but with `device_id = ''` — used as a fallback for records approved before the cookie anchor was introduced.

### Fingerprint Stability Factors

| Factor | Stable? | Risk |
|--------|---------|------|
| User-Agent | Semi-stable | Browser/OS updates break it |
| Accept-Language | Stable | Language setting changes break it |
| Accept-Encoding | Very stable | Rarely changes |
| IP Address | Unstable | ISP DHCP, VPN, mobile networks break it |
| Cookie (device_id) | Most stable | Cookie clearance = new identity |

---

## 5. Authorization Duration & Expiry

### ⚠️ CRITICAL FINDING: No Expiry Implemented

**Approved device authorizations have no time limit.** Once a device entry is written to `authorized_devices.json` with `"active": true`, it remains authorized indefinitely.

The `created_at` field is stored in the JSON but is **never checked** against any TTL or expiration logic in the middleware.

```json
{
  "fingerprint": "444be32e095db424f8b4ae5b1e5cf8bb",
  "created_at": "2026-02-11T14:59:00",  ← stored but NEVER checked for expiry
  "active": true                          ← only this controls access
}
```

### Authorization "Lifecycle" Summary

| Event | Mechanism | Duration |
|-------|-----------|----------|
| Cookie identity | Browser cookie | 2 years (or until cleared) |
| Device authorization | JSON file, `active: true` | **Indefinite** |
| Lockout (failed attempts) | Django cache | 30 minutes (configurable) |
| Daily transaction counter | Django cache | Until midnight (24h cache key) |
| Security alert cache | Django cache | 24 hours |

### Revocation

Authorization can be revoked manually via:
- `middleware.revoke_device(fingerprint)` — sets `"active": false` and stamps `revoked_at`
- Management command: `python manage.py device_auth revoke <fingerprint>`
- Admin interface (if implemented in the manage requests view)

Revocation is **manual** only. There is no scheduled job, rotation policy, or periodic re-authorization requirement.

---

## 6. Security Levels

### 6.1 Level Definitions

| Level | Numeric Rank | Description | Used For |
|-------|-------------|-------------|---------|
| `DEVELOPMENT` | 1 (aliased → STANDARD) | Debug/dev bypass semantics | Local dev only |
| `STANDARD` | 1 | Basic access to restricted paths | General staff terminals |
| `RESTRICTED` | 2 | Elevated — for API/transaction paths | Transaction terminals |
| `HIGH_SECURITY` | 3 | Full admin/delete privilege | Admin workstations |
| `MILITARY` | 3 (aliased → HIGH_SECURITY) | Same rank as HIGH_SECURITY | Armory terminals |

### 6.2 Level Assignment

- Set by admin during approval via `DeviceAuthorizationRequest.security_level`
- Default on approval: `HIGH_SECURITY` (enforced by the recovery/auto-approve logic in the view)
- No automatic downgrade after approval

### 6.3 Path-to-Level Mapping

```
Path matches exempt_paths    → No check required
Path matches high_security_paths (e.g. /admin/)   → Requires rank ≥ 3 (HIGH_SECURITY or MILITARY)
Path matches restricted_paths (e.g. /transactions/api/) → Requires rank ≥ 1 (STANDARD+)
protect_root_path = true     → All other paths require rank ≥ 3
```

### 6.4 Currently Configured Security Zones (production `authorized_devices.json`)

**Exempt (no auth check):**
```
/static/, /media/, /favicon.ico, /robots.txt
/login/, /accounts/login/, /logout/
/admin/device/request-authorization/
```

**Restricted paths (any authorized device):**
```
/transactions/create/, /transactions/api/, /inventory/api/
/admin/transactions/, /admin/inventory/, /qr_manager/generate/
/personnel/api/create/, /admin/core/, /admin/users/, /api/
/core/api/, /inventory/api/delete/, /transactions/api/delete/
/users/api/, /personnel/api/delete/
```

**High security paths (HIGH_SECURITY or MILITARY only):**
```
/admin/, /transactions/delete/, /users/delete/, /inventory/delete/
/admin/auth/, /personnel/delete/, /core/settings/
```

---

## 7. Path Protection Configuration

Path security is checked via `is_restricted_path(path)` which returns:

- `False` — path is exempt, skip all device checks
- `'RESTRICTED'` — path is sensitive, any authorized device passes
- `'HIGH_SECURITY'` — path requires HIGH_SECURITY or MILITARY level

With `protect_root_path = true` (current production setting), **any path** not explicitly exempt is treated as `HIGH_SECURITY`. This is a strict default, meaning new routes are secure-by-default.

---

## 8. Lockout & Rate Limiting

### 8.1 Brute-Force Lockout

| Parameter | Default | Location |
|-----------|---------|----------|
| Max failed attempts | 3 | `authorized_devices.json` → `max_failed_attempts` |
| Lockout duration | 30 minutes | `authorized_devices.json` → `lockout_duration_minutes` |
| Lockout storage | Django cache | Key: `device_lockout_<fingerprint>` |
| Attempt counter storage | Django cache | Key: `device_attempts_<fingerprint>`, expires 1 hour |

**Lockout triggers on:**
1. Fingerprint not found in JSON
2. IP address mismatch vs. bound IP

**Lockout does NOT trigger on:**
- Security level insufficient
- Outside active hours
- Daily transaction limit exceeded
- User not authorized for device

### ⚠️ Lockout Persistence Gap

Lockout state is stored in Django cache (memory/Redis). If the server restarts or cache is cleared, all lockouts are wiped and an attacker can immediately retry from scratch.

---

## 9. Active Hours Enforcement

Devices can have an optional `active_hours` constraint. When set, the device is only authorized within the specified time window.

### ⚠️ BUG: active_hours Format Mismatch

**The middleware expects `active_hours` as a dictionary:**
```python
start_time = time.fromisoformat(active_hours.get('start', '00:00:00'))
end_time = time.fromisoformat(active_hours.get('end', '23:59:59'))
```

**But `authorized_devices.json` stores it as a string:**
```json
"active_hours": "06:00-18:00"
```

**Calling `.get()` on a string raises `AttributeError`**, which will surface as an unhandled exception at `_is_within_active_hours()`, propagating up through `is_device_authorized()` and potentially crashing `process_request()`.

**Affected device:** `Armory PC Terminal` (the only device with `active_hours` in the current JSON)

**Fix required:** Either change the JSON format to `{"start": "06:00", "end": "18:00"}`, or update `_is_within_active_hours()` to parse both formats.

---

## 10. Transaction Limits

Per-device daily transaction limits are enforced only on paths containing the string `transaction` in the URL.

| Parameter | Default | Location |
|-----------|---------|----------|
| `max_daily_transactions` | 50 | JSON device entry / DB model field |
| Counter storage | Django cache | Key: `device_transactions_<fingerprint>_<date>` |
| Counter TTL | 86400 seconds (24h) | Cache timeout |
| Reset | Midnight UTC (key changes) | Date-based key |

### ⚠️ Transaction Counter Persistence Gap

Counter is stored in Django cache. A server restart resets all transaction counters to zero, allowing unlimited transactions that day regardless of prior activity.

---

## 11. Audit Trail — DeviceAccessLog

Every authorization check on a protected path (success or failure) is persisted to `DeviceAccessLog` in the database.

### Schema

| Field | Type | Description |
|-------|------|-------------|
| `checked_at` | DateTimeField | Timestamp of access attempt |
| `user` | FK → User (nullable) | Authenticated user (null if anonymous) |
| `path` | CharField(500) | Request URL path |
| `method` | CharField(10) | HTTP method (GET, POST, etc.) |
| `ip_address` | GenericIPAddressField | Client IP |
| `device_fingerprint` | CharField(64) | Device hash |
| `user_agent` | TextField | HTTP User-Agent header |
| `security_level` | CharField(20) | STANDARD / RESTRICTED / HIGH_SECURITY |
| `is_authorized` | BooleanField | Whether access was granted |
| `reason` | CharField(255) | Machine-readable denial reason code |
| `response_status` | PositiveSmallIntegerField | HTTP status returned (200 / 403) |

### Denial Reason Codes

| Code | Cause |
|------|-------|
| `authorized` | Access granted |
| `allow_all_debug` | Debug bypass (DEBUG mode) |
| `locked_out` | Too many failed attempts |
| `device_not_registered` | Fingerprint not in JSON |
| `insufficient_security_level_*` | Device rank below path requirement |
| `device_deactivated` | `active: false` in JSON |
| `ip_mismatch` | Request IP ≠ bound IP |
| `outside_active_hours` | Outside allowed time window |
| `daily_transaction_limit_exceeded` | Transaction cap reached |
| `user_not_authorized_for_device` | User not in device's `authorized_users` list |
| `mtls_required_but_not_verified_*` | mTLS required but client cert absent/invalid |

### Indexes

Optimized queries on:
- `checked_at` (latest-first ordering)
- `device_fingerprint + checked_at`
- `is_authorized + checked_at`
- `ip_address + checked_at`

The `audit_settings.retention_days = 90` is specified in the JSON config, but **there is no automated cleanup job** — logs will grow indefinitely unless manually purged.

---

## 12. mTLS Support

The middleware includes optional mutual TLS (mTLS) support for the highest security paths.

### How It Works

mTLS verification is performed by a trusted reverse proxy (e.g., nginx), which sets headers that Django reads:

| Header | Setting | Purpose |
|--------|---------|---------|
| `X-SSL-Client-Verify` | `MTLS_HEADER_VERIFY` | `SUCCESS` if cert valid |
| `X-SSL-Client-DN` | `MTLS_HEADER_DN` | Subject Distinguished Name |
| `X-SSL-Client-Serial` | `MTLS_HEADER_SERIAL` | Certificate serial number |
| `X-SSL-Client-Fingerprint` | `MTLS_HEADER_FINGERPRINT` | Certificate fingerprint |

### Activation Requirements

```python
# settings.py
MTLS_ENABLED = True
MTLS_REQUIRED_SECURITY_LEVEL = 'HIGH_SECURITY'  # Apply to HIGH_SECURITY+ paths
MTLS_TRUST_PROXY_HEADERS = True                  # Trust the reverse proxy headers
```

### CSR/Certificate Workflow

The authorization request form accepts a PEM certificate signing request (CSR). Upon admin approval, the system can automatically issue a certificate. This enables seamless mTLS for approved devices.

### Current Status

`MTLS_ENABLED` defaults to `False`. mTLS is fully implemented in code but **not active in the current deployment**.

---

## 13. Pros & Strengths

### 13.1 Defense-in-Depth
Device authorization runs as a separate layer from user authentication. Even a compromised user account cannot access the system from an unauthorized device.

### 13.2 Cookie-Anchored Fingerprinting
The `armguard_device_id` cookie acts as a stable identity anchor. This is more reliable than UA/IP-only fingerprinting which breaks on network or browser changes.

### 13.3 Tiered Security Zones
The three-tier path system (exempt / restricted / high-security) allows fine-grained control. New paths default to HIGH_SECURITY (`protect_root_path = true`), which is a **secure-by-default** posture.

### 13.4 Comprehensive Audit Trail
Every access attempt (authorized or denied) is logged to the database with enough detail for forensic reconstruction. Indexed fields allow efficient querying by device, IP, and time range.

### 13.5 Per-Device Policy Configuration
Each device can have its own security level, transaction limits, active hours, IP binding, and user binding. This allows operating differentiated security postures per terminal (e.g., armory terminal vs. admin workstation).

### 13.6 Brute-Force Lockout
3 failed attempts triggers a 30-minute lockout — effective against online brute-force of device fingerprints.

### 13.7 mTLS Infrastructure Ready
Full PKI/mTLS support is implemented and only needs activation. This is a high-security capability rarely seen in custom Django applications.

### 13.8 Fingerprint Rotation
The `rotate_device_fingerprint()` method allows safe migration of device identity (e.g., after browser reset) without losing authorization history. Old fingerprint is archived.

### 13.9 Management CLI
A `python manage.py device_auth` management command is available for administrative operations without accessing the web interface.

### 13.10 Auto-Recovery Logic
The view handles multiple edge cases (stale approvals, incognito sessions, IP changes) automatically, reducing administrative overhead.

---

## 14. Cons & Risks

### 14.1 ⚠️ No Authorization Expiry (HIGH)
**Risk:** A compromised device remains authorized indefinitely. There is no re-validation period, rotation schedule, or expiry date for any authorization.  
**Impact:** A stolen authorized laptop or device cookie remains a valid entry point forever unless manually revoked.

### 14.2 ⚠️ Cache-Backed Lockout (HIGH)
**Risk:** Lockout state and transaction counters are stored in Django cache (in-memory or Redis without AOF/snapshot). A server restart resets all lockouts.  
**Impact:** An attacker can trigger a brute-force attempt, wait for a restart (e.g., during maintenance), and retry immediately.

### 14.3 ⚠️ Flat File Authorization Store (MEDIUM)
**Risk:** `authorized_devices.json` is a plain text file with no access controls beyond OS file permissions. It can be read or modified by anyone with filesystem access.  
**Impact:** A compromised server account could add unauthorized devices directly to the JSON file, bypassing the approval workflow entirely.

### 14.4 ⚠️ Active Hours Format Bug (MEDIUM)
**Risk:** The `Armory PC Terminal` device has `active_hours: "06:00-18:00"` (string) but the code calls `.get()` on it as if it were a dict.  
**Impact:** An AttributeError will crash authorization for this device and propagate as a 500 error. Active hours restriction is effectively broken.

### 14.5 ⚠️ Header-Based Fingerprint Spoofability (MEDIUM)
**Risk:** The fingerprint includes `Accept-Language`, `Accept-Encoding`, and `User-Agent` — all of which can be freely set by an attacker. If the attacker has access to the device cookie (e.g., via network interception without HTTPS, or XSS), they can replay the full fingerprint.  
**Impact:** The fingerprint offers weak identity assurance if the cookie is compromised.

### 14.6 ⚠️ O(n) Linear Scan for Device Lookup (MEDIUM)
**Risk:** `is_device_authorized()` performs a linear scan of all devices on every request to a restricted path. With many devices this scales poorly.  
**Impact:** Performance degradation as the device list grows. Negligible for < 50 devices, noticeable at > 500.

### 14.7 ⚠️ Middleware Loads JSON on Init Only (MEDIUM)
**Risk:** `authorized_devices.json` is loaded once at middleware instantiation. Changes to the file are not reflected until the server restarts or `middleware.load_authorized_devices()` is explicitly called.  
**Impact:** In a multi-worker/Gunicorn setup, each worker has its own cached copy. Approving a device via one worker does not immediately propagate to other workers.

### 14.8 No Audit Log Retention Enforcement (LOW)
**Risk:** `audit_settings.retention_days = 90` is defined in the config but there is no scheduled job to delete old `DeviceAccessLog` records.  
**Impact:** Database grows unbounded; sensitive access records persist longer than intended.

### 14.9 Superuser DEBUG Bypass (LOW)
**Risk:** In DEBUG mode (`settings.DEBUG = True`), requests from `is_superuser` accounts entirely skip device authorization (`process_request` returns `None` immediately).  
**Impact:** If DEBUG is accidentally left enabled in production, all superusers bypass device auth.

### 14.10 Legacy IP-Only Match (LOW)
**Risk:** Devices in the JSON without a `fingerprint` field are matched on IP address alone.  
**Impact:** Any device on the same IP (LAN peers, NAT) could pass as an authorized device.

---

## 15. Bug Report: Active Hours Parsing

**File:** `core/middleware/device_authorization.py`  
**Method:** `_is_within_active_hours(device_config)`  
**Affected device:** Any device with `active_hours` stored as a string in `authorized_devices.json`

### Current (Broken) Code

```python
def _is_within_active_hours(self, device_config):
    active_hours = device_config.get('active_hours')
    if not active_hours:
        return True
    
    current_time = timezone.now().time()
    start_time = time.fromisoformat(active_hours.get('start', '00:00:00'))  # ← BUG: str has no .get()
    end_time = time.fromisoformat(active_hours.get('end', '23:59:59'))      # ← BUG
```

### Proposed Fix

```python
def _is_within_active_hours(self, device_config):
    active_hours = device_config.get('active_hours')
    if not active_hours:
        return True
    
    current_time = timezone.now().time()
    
    # Support both dict {'start': 'HH:MM', 'end': 'HH:MM'} and string 'HH:MM-HH:MM'
    if isinstance(active_hours, str):
        parts = active_hours.split('-')
        if len(parts) == 2:
            start_str, end_str = parts[0].strip(), parts[1].strip()
        else:
            return True  # Invalid format, allow access
    elif isinstance(active_hours, dict):
        start_str = active_hours.get('start', '00:00')
        end_str = active_hours.get('end', '23:59')
    else:
        return True  # Unknown format, allow access
    
    try:
        # Pad to full HH:MM:SS if needed
        if start_str.count(':') == 1:
            start_str += ':00'
        if end_str.count(':') == 1:
            end_str += ':00'
        start_time = time.fromisoformat(start_str)
        end_time = time.fromisoformat(end_str)
    except ValueError:
        return True  # Malformed time, allow access
    
    if start_time <= end_time:
        return start_time <= current_time <= end_time
    else:
        return current_time >= start_time or current_time <= end_time
```

Also update `authorized_devices.json` for the Armory PC Terminal to use the dict format:
```json
"active_hours": {"start": "06:00", "end": "18:00"}
```

---

## 16. Security Improvement Recommendations

### Priority 1 — Critical (Implement Immediately)

#### 1.1 Add Authorization Expiry / Periodic Re-validation

```json
// authorized_devices.json device entry addition:
{
  "fingerprint": "...",
  "active": true,
  "created_at": "2026-02-11T14:59:00",
  "expires_at": "2027-02-11T14:59:00",   ← ADD THIS
  "last_validated": "2026-11-01T08:00:00" ← ADD THIS (periodic re-auth)
}
```

Add to `is_device_authorized()`:
```python
# Check expiry
expires_at = device_config.get('expires_at')
if expires_at:
    if timezone.now() > datetime.fromisoformat(expires_at):
        self._last_auth_reason = 'authorization_expired'
        return False
```

Recommended defaults:
- Standard devices: 1-year expiry
- High-security/military: 90-day expiry with 30-day re-validation

#### 1.2 Persist Lockout State to Database

Move lockout state from Django cache to a database table so it survives server restarts:

```python
# New model: DeviceLockout
class DeviceLockout(models.Model):
    device_fingerprint = models.CharField(max_length=64, unique=True, db_index=True)
    locked_until = models.DateTimeField()
    attempts = models.PositiveIntegerField(default=0)
    last_attempt_ip = models.GenericIPAddressField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

#### 1.3 Fix Active Hours Bug

Apply the fix described in §15 immediately. The Armory PC Terminal currently has broken active-hours enforcement.

---

### Priority 2 — High (Implement This Sprint)

#### 2.1 Move Authorization Store to Database

Replace `authorized_devices.json` with a proper database-backed store:
- Atomic updates across multiple workers
- Row-level locking prevents race conditions
- DB backups include authorization state
- No risk of corruption from concurrent writes

#### 2.2 Pre-Index Fingerprints in Memory

Cache a fingerprint→device dict on load to make lookups O(1) instead of O(n):

```python
def load_authorized_devices(self):
    # ... existing load logic ...
    self._fingerprint_index = {
        d['fingerprint']: d 
        for d in self.authorized_devices['devices'] 
        if d.get('fingerprint')
    }
```

#### 2.3 Enforce Audit Log Retention

Add a management command or celery task:
```python
# management/commands/purge_device_logs.py
DeviceAccessLog.objects.filter(
    checked_at__lt=timezone.now() - timedelta(days=settings.DEVICE_LOG_RETENTION_DAYS)
).delete()
```

Schedule via cron: `0 2 * * * python manage.py purge_device_logs`

#### 2.4 Enable mTLS for HIGH_SECURITY Paths

With mTLS infrastructure already in place, activating it provides hardware-level device attestation:
```python
# settings.py
MTLS_ENABLED = True
MTLS_REQUIRED_SECURITY_LEVEL = 'HIGH_SECURITY'
```

Requires nginx configuration with `ssl_verify_client on;`.

---

### Priority 3 — Medium (Next Planning Cycle)

#### 3.1 Device Certificate Pinning

Issue unique client certificates per device. Bind the certificate serial number to the device entry. This makes identity forgery cryptographically hard.

#### 3.2 IP Range Binding

Instead of exact IP matching, support CIDR notation for device locations:
```json
"allowed_ip_ranges": ["192.168.0.0/24", "10.0.1.0/28"]
```

#### 3.3 Geographic / Network Restrictions

Add network-segment awareness: devices should only be accessible from expected subnets (armory LAN, admin VLAN).

#### 3.4 Anomaly Detection Hook

Flag and alert on behavioral anomalies:
- Device fingerprint seen from new IP (outside normal range)
- Unusual access time patterns
- Sudden spike in transaction attempts
- Access from multiple IPs within a short window

#### 3.5 Periodic Background Revalidation

For active sessions, re-check authorization at interval (e.g., every 15 minutes):
```python
# In process_request: check session-level cache
last_validated_key = f"device_last_validated_{fingerprint}"
if not cache.get(last_validated_key):
    # Force re-check against JSON/DB
    cache.set(last_validated_key, True, timeout=900)  # 15 min
```

#### 3.6 Two-Factor Device Approval

Require a second administrator to countersign approvals for MILITARY-level devices (four-eyes principle).

#### 3.7 Remove Legacy IP-Only Matching

All active devices should have a fingerprint. Audit the JSON to ensure no fingerprint-less legacy entries remain.

---

## 17. Compliance Claims vs. Reality

The `authorized_devices.json` claims compliance with the following standards:

```json
"security_compliance": {
  "nist_800_53": true,
  "fisma_moderate": true,
  "owasp_2021": true,
  "military_standards": true
}
```

### Gap Analysis

| Standard | Key Requirement | Status |
|----------|----------------|--------|
| **NIST 800-53 IA-3** (Device Identification) | Re-authentication required periodically | ❌ No expiry |
| **NIST 800-53 AC-12** (Session Termination) | Terminate sessions after inactivity | ❌ Not implemented |
| **NIST 800-53 AU-11** (Audit Record Retention) | Retain logs per org policy | ⚠️ Policy defined, no enforcement |
| **NIST 800-53 SI-3** (Malicious Code Protection) | Integrity check for config files | ❌ JSON has no signature/hash |
| **FISMA Moderate** | NIST 800-53 at moderate baseline | ⚠️ Partial (see above gaps) |
| **OWASP 2021 A07** (Auth Failures) | Protect against brute-force | ✅ Lockout implemented (but cache-backed) |
| **OWASP 2021 A02** (Crypto Failures) | Secure cookies, HTTPS enforcement | ✅ httponly, secure flag in production |
| **Military Standards** | Role-based + terminal-bound access | ✅ Role binding, terminal binding |

### Summary

The compliance claims are **aspirational rather than certified**. Significant gaps exist in expiry/re-authentication (NIST IA-3), audit retention enforcement (NIST AU-11), and config integrity (NIST SI-3).

---

## Appendix: Current Authorized Devices Summary (authorized_devices.json)

| Device | IP | Security Level | Transactions | Active Hours | Roles |
|--------|-----|---------------|-------------|-------------|-------|
| Localhost Development | 127.0.0.1 | DEVELOPMENT | 1000/day | Unrestricted | admin, development, superuser |
| Developer PC | 192.168.0.82 | HIGH_SECURITY | 100/day | Unrestricted | admin, development |
| Armory PC Terminal | 192.168.0.100 | MILITARY | 200/day | "06:00-18:00" ⚠️ (bug) | armory, transactions |

**Note:** The Armory PC Terminal does not have a `fingerprint` field — it relies on the legacy IP-only match.

---

*End of ARMGUARD RDS Device Authorization Security Review*
