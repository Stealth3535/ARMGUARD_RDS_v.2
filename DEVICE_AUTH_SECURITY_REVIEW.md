# ARMGUARD RDS — Device Authorization System: Security Review & Enterprise Redesign

> **Prepared by:** GitHub Copilot — Senior Cybersecurity Architect  
> **Version:** 2.0 — Enterprise Redesign  
> **Scope:** Full system audit (v1) + Production-ready redesign (v2)  
> **Files:** `core/device/` (new), `core/middleware/device_authorization.py` (v1 legacy)  
> **Classification:** Internal — Security Sensitive  
> **Standards:** OWASP ASVS v4.0 L2 · NIST SP 800-63B · NIST SP 800-207 (Zero Trust) · FISMA Moderate

---

## Table of Contents

### Part I — v1 System Audit
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

### Part II — v2 Enterprise Redesign
16. [Security Assessment Summary](#16-security-assessment-summary)
17. [Threat Model](#17-threat-model)
18. [New Architecture Design](#18-new-architecture-design)
19. [Code Implementation Overview](#19-code-implementation-overview)
20. [Database Schema](#20-database-schema)
21. [Security Controls Added](#21-security-controls-added)
22. [MFA Integration](#22-mfa-integration)
23. [Testing Strategy](#23-testing-strategy)
24. [Compliance Gap Closure](#24-compliance-gap-closure)
25. [Deployment & Migration Plan](#25-deployment--migration-plan)

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
**Status:** ✅ **FIXED** in commit `b47be146`

### Root Cause

The middleware called `active_hours.get('start', ...)` but `authorized_devices.json` stores the field as `"06:00-18:00"` (a string). Strings have no `.get()` method → `AttributeError` crash on every request for the Armory PC Terminal.

### Fix Applied

Both string (`"HH:MM-HH:MM"`) and dict (`{"start": "HH:MM", "end": "HH:MM"}`) formats are now parsed with full error tolerance. The Armory PC Terminal's active-hours restriction is now enforced correctly.

---

# Part II — v2 Enterprise Redesign

---

## 16. Security Assessment Summary

### Overall v1 Verdict

| Domain | Score | Finding |
|--------|-------|---------|
| Device Identity | 3/10 | Header-based fingerprint + cookie — trivially spoofable |
| Authorization Lifecycle | 2/10 | No expiry; indefinite trust once approved |
| Credential Management | 2/10 | No MFA during enrollment; no key binding |
| Audit & Forensics | 7/10 | Good DB log; lacks SIEM fields and retention enforcement |
| Anomaly Detection | 0/10 | Not implemented |
| Separation of Concerns | 3/10 | All logic in middleware; no service layer |
| Compliance | 4/10 | Claims NIST/FISMA; major IA-3, AC-12, AU-11 gaps |

### Critical Weaknesses Driving Redesign

1. **MAC header (`HTTP_X_CLIENT_MAC`) trivially spoofed** — any HTTP client can set this header
2. **No device authorization expiry** — perpetual trust violates Zero Trust principles  
3. **No MFA on enrollment** — anyone with a user account can register any device  
4. **No cryptographic binding** — no proof that the device is actually the authorized hardware  
5. **Flat JSON storage** — no transactions, no integrity, breaks in multi-worker deployments  
6. **Logic in middleware** — impossible to test, reuse, or extend independently

---

## 17. Threat Model

### Assets

| Asset | Value | Current Controls |
|-------|-------|-----------------|
| Armory transaction terminal | CRITICAL | IP binding, role binding |
| Admin workstation | HIGH | Security tier check |
| Authorized device token | HIGH | Cookie (httponly), no expiry ⚠️ |
| Personnel / inventory data | HIGH | Auth + device check |
| Device approval workflow | HIGH | Admin review only |

### Threat Actors

| Actor | Capability | Motivation |
|-------|-----------|------------|
| External attacker | Low–Medium | Data theft, ransomware pivot |
| Malicious insider | High | Privilege escalation, data exfiltration |
| Stolen device | Physical access | Use of pre-authorized device |
| Network adversary (LAN) | Medium | IP spoofing, session hijack |

### STRIDE Analysis

| Threat | Vector | v1 Mitigated? | v2 Mitigation |
|--------|--------|--------------|---------------|
| **Spoofing** — forged headers | HTTP_X_CLIENT_MAC / UA | ❌ No | Cryptographic device token; optional key pair |
| **Spoofing** — stolen cookie | Cookie theft | ⚠️ Partial (httponly) | Signed device token + IP binding + risk scoring |
| **Tampering** — JSON edit | Filesystem access | ❌ No | DB storage with transaction integrity |
| **Repudiation** — deny access | No per-event log | ⚠️ Partial | Immutable `DeviceAuditEvent` log |
| **Info Disclosure** — log exposure | DB logs | ✅ DB Only | SIEM export; token prefix only in logs |
| **Denial of Service** — lockout abuse | Rate limit on fingerprint | ⚠️ Cache-only | DB-backed lockout; rate limiter on enroll endpoint |
| **Elevation of Privilege** — tier bypass | Security rank check | ✅ | Maintained + re-validation requirement |

### Attack Scenarios

**Scenario 1: Stolen Laptop (Authorized Device)**
- v1: Perpetual access — device remains authorized forever
- v2: 90-day expiry; risk score spikes on new IP anomaly; auto-suspend on threshold

**Scenario 2: Insider Registers Unauthorized Device via Different Network**
- v1: Possible if user account is compromised; no MFA gate
- v2: TOTP/email OTP required before request reaches admin queue; admin must approve

**Scenario 3: Network Attacker Spoofs IP of Authorized Terminal**
- v1: IP binding blocks exact-IP mismatch, but fingerprint (UA/headers) is spoofable
- v2: Cryptographic device token cannot be guessed; token is never in URL/headers (httponly cookie only); optional mutual TLS

**Scenario 4: Server Restart Clears Lockout — Brute Force Resume**
- v1: Django cache reset → lockout cleared → attacker retries immediately
- v2: Lockout stored in `AuthorizedDevice.locked_until` field (DB-persistent)

---

## 18. New Architecture Design

### Architectural Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Browser / API Client                            │
│  Cookie: armguard_device_token (httponly, secure, 2y, 64-char hex)      │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │ HTTP Request
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│              DeviceAuthMiddleware  (thin adapter — HTTP only)           │
│  1. call device_service.authorize_request(request)                      │
│  2. if denied → 403 JSON or redirect                                    │
│  3. attach request.device_decision for downstream views                 │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    DeviceService  (facade)                              │
├───────────────┬───────────────────┬──────────────────┬─────────────────┤
│ PathSecurity  │  DeviceIdentity   │  DeviceRisk       │  Decision       │
│ Resolver      │  Service          │  Evaluator        │  Engine         │
│               │                   │                   │                 │
│ Reads         │ token → DB lookup │ new IP?           │ is_active?      │
│ DEVICE_PATH   │ resolve device    │ UA changed?       │ tier check      │
│ _CONFIG from  │ (no header hash!) │ velocity spike?   │ IP binding      │
│ settings      │                   │ concurrent IPs?   │ active hours    │
│               │                   │ → risk_score bump │ revalidation?   │
│               │                   │ → alert dispatch  │ risk threshold  │
└───────────────┴───────────────────┴──────────────────┴─────────────────┘
                                    │
                     ┌──────────────▼──────────────┐
                     │       Django ORM / DB        │
                     ├──────────────────────────────┤
                     │  AuthorizedDevice            │
                     │  DeviceAuditEvent (append)   │
                     │  DeviceAccessLog             │
                     │  DeviceRiskEvent             │
                     │  DeviceMFAChallenge          │
                     └──────────────────────────────┘
```

### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Server-issued opaque token** as identity anchor | Cannot be guessed or derived from request headers; replaces SHA-256(UA\|IP\|cookie) |
| **DB-backed device records** | Survives restarts; atomic updates; auditable schema migrations |
| **MFA gate before admin queue** | Proves the enrolling user controls a second factor; prevents insider auto-registration |
| **Service layer pattern** | Logic is testable without Django request machinery; reusable in management commands, API views |
| **Immutable audit events** | Append-only table; integrity preserved even if main record changes |
| **Risk scoring** | Enables graduated response (alert → suspend → block) rather than binary allow/deny |
| **Per-path config in settings** | Ops team can adjust security zones without changing code |

### Zero Trust Alignment

| ZT Principle | v1 | v2 |
|-------------|----|----|
| Never trust, always verify | ⚠️ Trust persists indefinitely | ✅ Re-evaluated per request; expiry enforced |
| Verify explicitly | ⚠️ Header fingerprint | ✅ DB token + optional mTLS/key pair |
| Least privilege access | ✅ Security tiers | ✅ Tiers + role binding + active hours |
| Assume breach | ❌ No anomaly detection | ✅ Risk evaluator + alerts + auto-suspend |

---

## 19. Code Implementation Overview

All new code is in `armguard/core/device/`:

| File | Purpose |
|------|---------|
| `models.py` | `AuthorizedDevice`, `DeviceAuditEvent`, `DeviceMFAChallenge`, `DeviceAccessLog`, `DeviceRiskEvent` |
| `service.py` | `DeviceService` facade + sub-services (`PathSecurityResolver`, `DeviceIdentityService`, `DeviceRiskEvaluator`, `AuthorizationDecisionEngine`) |
| `mfa.py` | `TOTPService` (pyotp wrapper), `EmailOTPService`, `MFAReadinessCheck` |
| `middleware.py` | `DeviceAuthMiddleware` — thin adapter, delegates entirely to `device_service` |
| `migration_seed.py` | Data migration script: reads `authorized_devices.json` → seeds `AuthorizedDevice` table |
| `tests.py` | 40+ test cases: unit, integration, penetration |

### Settings Reference

```python
# settings.py additions for v2

DEVICE_AUTH_EXPIRY_DAYS        = 90      # Days before re-authorization required
DEVICE_EXPIRY_WARNING_DAYS     = 14      # Days before expiry to warn user
DEVICE_MAX_FAILED_ATTEMPTS     = 5       # Before DB-persisted lockout
DEVICE_LOCKOUT_MINUTES         = 30      # Lockout duration
DEVICE_RISK_BLOCK_THRESHOLD    = 75      # Risk score that triggers hard block
DEVICE_VELOCITY_THRESHOLD      = 120     # Requests/minute before risk event
DEVICE_MFA_CHALLENGE_TTL_MINUTES = 15   # OTP / TOTP challenge window
DEVICE_TOKEN_COOKIE            = 'armguard_device_token'
DEVICE_COOKIE_MAX_AGE          = 63_072_000  # 2 years in seconds
DEVICE_ALERT_EMAIL             = 'security@armguard.mil'  # Risk alert destination
DEVICE_TOTP_CACHE_FALLBACK     = False   # True only while profile migration pending

DEVICE_PATH_CONFIG = {
    'protect_root_path': True,  # All unmatched paths → HIGH_SECURITY
    'exempt': ['/static/', '/media/', '/login/', '/accounts/login/',
               '/logout/', '/admin/device/request-authorization/'],
    'restricted': ['/transactions/', '/inventory/api/', '/qr_manager/generate/',
                   '/api/', '/personnel/api/'],
    'high_security': ['/admin/', '/transactions/delete/', '/users/delete/',
                      '/inventory/delete/', '/core/settings/'],
}
```

---

## 20. Database Schema

### AuthorizedDevice

```
┌─────────────────────────────────────────────────────────────────┐
│ AuthorizedDevice                                                │
├──────────────────────────┬──────────────────────────────────────┤
│ id                       │ UUIDField (PK, auto)                 │
│ device_token             │ CharField(64), unique — server-issued│
│ public_key_pem           │ TextField, optional — device keypair │
│ public_key_fingerprint   │ CharField(64), indexed               │
│ device_name              │ CharField(255)                       │
│ device_type              │ CharField(64)                        │
│ user                     │ FK → User                            │
│ ip_first_seen            │ GenericIPAddressField                │
│ ip_last_seen             │ GenericIPAddressField                │
│ ip_binding               │ GenericIPAddressField (optional)     │
│ user_agent_hash          │ CharField(64)                        │
│ enrolled_at              │ DateTimeField (auto)                 │
│ authorized_at            │ DateTimeField (nullable)             │
│ expires_at               │ DateTimeField (default: now+90d)     │
│ last_used                │ DateTimeField (nullable)             │
│ revoked_at               │ DateTimeField (nullable)             │
│ status                   │ CharField: PENDING_MFA/PENDING/      │
│                          │   ACTIVE/EXPIRED/REVOKED/SUSPENDED   │
│ security_tier            │ CharField: STANDARD/RESTRICTED/      │
│                          │   HIGH_SECURITY/MILITARY             │
│ can_transact             │ BooleanField                         │
│ max_daily_transactions   │ PositiveIntegerField                 │
│ active_hours_start       │ TimeField (nullable)                 │
│ active_hours_end         │ TimeField (nullable)                 │
│ authorized_roles         │ JSONField (list of role names)       │
│ risk_score               │ PositiveSmallIntegerField (0-100)    │
│ failed_auth_count        │ PositiveIntegerField                 │
│ locked_until             │ DateTimeField (nullable) — DB-backed │
│ enrollment_reason        │ TextField                            │
│ reviewed_by              │ FK → User (nullable)                 │
│ reviewed_at              │ DateTimeField (nullable)             │
│ review_notes             │ TextField                            │
│ revoke_reason            │ TextField                            │
│ last_revalidated_at      │ DateTimeField (nullable)             │
│ revalidation_required    │ BooleanField                         │
└──────────────────────────┴──────────────────────────────────────┘
```

### DeviceAuditEvent (append-only)

```
┌─────────────────────────────────────────────────────────────────┐
│ DeviceAuditEvent                                                │
├──────────────────────────┬──────────────────────────────────────┤
│ id                       │ BigAutoField (PK)                    │
│ device                   │ FK → AuthorizedDevice                │
│ event_type               │ CharField(30): ENROLLED, MFA_PASSED, │
│                          │   ACTIVATED, REVOKED, TOKEN_ROTATED, │
│                          │   IP_ANOMALY, AUTH_SUCCESS, etc.     │
│ actor                    │ FK → User (nullable for auto-events) │
│ notes                    │ TextField                            │
│ ip_address               │ GenericIPAddressField (nullable)     │
│ occurred_at              │ DateTimeField (indexed)              │
│ metadata                 │ JSONField — SIEM-compatible          │
└──────────────────────────┴──────────────────────────────────────┘
```

### DeviceMFAChallenge

```
┌─────────────────────────────────────────────────────────────────┐
│ DeviceMFAChallenge                                              │
├──────────────────────────┬──────────────────────────────────────┤
│ id                       │ UUIDField (PK)                       │
│ device                   │ OneToOneField → AuthorizedDevice     │
│ method                   │ CharField: TOTP | EMAIL              │
│ otp_hash                 │ CharField(64) — SHA-256 + salt       │
│ otp_salt                 │ CharField(32)                        │
│ attempts                 │ PositiveSmallIntegerField            │
│ max_attempts             │ PositiveSmallIntegerField (5)        │
│ created_at               │ DateTimeField (auto)                 │
│ expires_at               │ DateTimeField (15min TTL)            │
│ verified_at              │ DateTimeField (nullable)             │
└──────────────────────────┴──────────────────────────────────────┘
```

### DeviceRiskEvent

```
┌─────────────────────────────────────────────────────────────────┐
│ DeviceRiskEvent                                                 │
├──────────────────────────┬──────────────────────────────────────┤
│ id                       │ BigAutoField (PK)                    │
│ device                   │ FK → AuthorizedDevice                │
│ risk_type                │ NEW_IP / IP_OUTSIDE / OFF_HOURS /    │
│                          │   HIGH_VELOCITY / CONCURRENT_IP /    │
│                          │   USER_AGENT_CHANGE / SUSPICIOUS_PATH│
│ severity                 │ PositiveSmallIntegerField (1-50)     │
│ detail                   │ TextField                            │
│ ip_address               │ GenericIPAddressField (nullable)     │
│ detected_at              │ DateTimeField (indexed)              │
│ acknowledged             │ BooleanField                         │
│ acknowledged_by          │ FK → User (nullable)                 │
└──────────────────────────┴──────────────────────────────────────┘
```

---

## 21. Security Controls Added

### Controls Matrix vs. v1

| Control | v1 Status | v2 Implementation |
|---------|-----------|-------------------|
| Device identity | Header fingerprint (spoofable) | Server-issued 256-bit opaque token |
| Cryptographic binding | None | Optional device key pair (PEM); challenge-response ready |
| MFA on enrollment | None | TOTP or Email OTP required before admin queue |
| Authorization expiry | None | `expires_at` field; configurable (default 90 days) |
| Auto re-validation | None | `revalidation_required` flag + `revalidate()` method |
| Brute-force lockout | Cache (lost on restart) | `locked_until` in DB — survives restarts |
| Anomaly detection | None | IP change, UA change, velocity, concurrent IPs |
| Risk scoring | None | 0–100 risk score; auto-suspend at threshold |
| Audit trail | Per-request log | Per-request `DeviceAccessLog` + per-event `DeviceAuditEvent` (append-only) |
| SIEM export | None | `siem_metadata` JSONField on every log row |
| Security alerts | Cache (24h, lossy) | Email + persistent `DeviceRiskEvent` DB rows |
| Transaction limits | Cache (lost on restart) | DB-backed (can be migrated; see §25) |
| Active hours | Dict/string format bug | `active_hours_start` / `active_hours_end` TimeFields — proper DB types |
| Multi-worker safety | JSON file per-worker | Single DB source of truth |
| Secret integrity | Plain JSON file | DB with ORM access control + migration history |
| Revocation | Manual + cache clear | `revoke()` DB method + `DeviceAuditEvent` entry |
| Token rotation | None | `rotate_token()` method with audit trail |
| Separation of concerns | Monolithic middleware | Service layer pattern; middleware is thin adapter |

### Security Properties

```
Confidentiality: Device tokens are httponly cookies — JS cannot read them.
                 OTP auth codes are stored as salted SHA-256 hashes only.
                 Audit logs store only token PREFIX (8 chars), not full token.

Integrity:       DB transactions prevent partial state on approval.
                 DeviceAuditEvent table is append-only (never UPDATE/DELETE).
                 Risk events are immutable and require acknowledgement.

Availability:    Exempt paths (static, login) bypass all device checks.
                 DB-backed lockout survives restarts.
                 Service layer returns fast AuthDecision even if DB is slow.

Non-repudiation: Every state change records actor + timestamp + notes.
                 auth_success / auth_denied logged per request with full context.
```

---

## 22. MFA Integration

### TOTP (Authenticator App) Flow

```
1. User visits /admin/device/request-authorization/
         │
         ▼
2. If user has no TOTP secret:
     TOTPService(user).get_or_create_secret()
     → QR code displayed (provisioning URI)
     → User scans with Google Authenticator / Authy
         │
         ▼
3. User submits enrollment form + TOTP code
         │
         ▼
4. device_service.enroll_device()
     → AuthorizedDevice created (status=PENDING_MFA)
     → DeviceMFAChallenge created
         │
         ▼
5. device_service.complete_mfa(device, totp_valid=TOTPService(user).verify(code))
     → status → PENDING (admin queue)
         │
         ▼
6. Admin approves → device.activate() → status=ACTIVE
```

### Email OTP Flow

```
1. User submits enrollment form (no TOTP app configured)
         │
         ▼
2. EmailOTPService.issue(device, challenge)
     → 6-digit code sent to user.email
     → Code stored as SHA-256(code+salt) on challenge record
         │
         ▼
3. User submits OTP from inbox
         │
         ▼
4. EmailOTPService.verify(challenge, submitted_code)
     → challenge.verify_email_otp() checks hash
     → Rate limited: max 3 emails per 2 minutes
     → Max 5 attempts; expires after 15 minutes
         │
         ▼
5. On success: device.status → PENDING
```

### Required Dependency

```bash
pip install pyotp qrcode[pil]   # TOTP + QR code generation
```

Add to `requirements.txt`:
```
pyotp>=2.9.0
qrcode[pil]>=7.4
```

---

## 23. Testing Strategy

### Test Coverage in `core/device/tests.py`

| Category | Tests | Key Assertions |
|----------|-------|----------------|
| Path Security Resolver | 5 | Static exempt, admin HIGH_SECURITY, unknown path with protect_root |
| Device Identity Service | 6 | Valid/invalid token formats, cookie presence, DB lookup |
| Authorization Decision Engine | 14 | All status states, tier checks, IP binding, lockout, risk, revalidation, active hours |
| Device Lifecycle (model) | 8 | activate, revoke, expire, revalidate, rotate_token, lockout, expiry warning, audit events |
| MFA Challenges | 5 | Correct OTP, wrong OTP, expired, exhausted, replay |
| Security / Penetration | 9 | Revoked replay, expired bypass, tier downgrade, IP spoof, lockout brute-force, risk block, pending-MFA access, force-revalidation bypass, unknown token |
| Risk Evaluator | 2 | New IP alert, same IP no alert |
| Service Integration | 5 | Exempt path, active device, missing cookie denied, superuser DEBUG bypass, enrollment flow |

### Running Tests

```bash
cd armguard
python manage.py test core.device.tests --verbosity=2
```

### Penetration Test Checklist

```
☐ Forge device token cookie  → must return 403
☐ Reuse revoked device token → must return 403
☐ Use expired device token   → must return 403
☐ Access /admin/ with STANDARD tier device → must return 403
☐ Modify IP binding and access from different IP → must return 403
☐ Submit >5 wrong tokens rapidly → must trigger DB lockout
☐ Clear Django cache after lockout → lockout must persist (DB)
☐ Skip MFA during enrollment → device must remain PENDING_MFA
☐ Submit expired OTP code → must fail
☐ Submit correct OTP twice (replay) → second must fail
☐ Set high risk_score via DB → access must be blocked at threshold
☐ Set revalidation_required=True → access must be blocked
☐ Access armory terminal outside 06:00-18:00 → must return 403
☐ Inject X-Forwarded-For to spoof bound IP → must return 403 (IP binding checks REMOTE_ADDR or trusted proxy)
```

---

## 24. Compliance Gap Closure

| Standard | Control | v1 Gap | v2 Closure |
|----------|---------|--------|------------|
| NIST 800-53 **IA-3** | Device Identification | No cryptographic device ID | Server-issued token; optional PEM key pair |
| NIST 800-53 **IA-3 (1)** | Cryptographic Bidirectional Authentication | Not implemented | Key pair + challenge-response framework ready |
| NIST 800-53 **IA-5** | Authenticator Management | No rotation, no expiry | `rotate_token()`, `expires_at`, `revalidate()` |
| NIST 800-53 **AC-12** | Session Termination | Not implemented | `revalidation_required` flag; expiry-driven re-auth |
| NIST 800-53 **AU-9** | Protection of Audit Information | Mutable DB rows | `DeviceAuditEvent` is append-only |
| NIST 800-53 **AU-11** | Audit Record Retention | No enforcement | `DeviceAccessLog` + management command hook for `retention_days` |
| NIST 800-53 **SI-3** | Malicious Code / Config Integrity | JSON plaintext | DB storage; no direct file manipulation |
| NIST 800-53 **SI-4** | System Monitoring | No anomaly detection | `DeviceRiskEvaluator` + `DeviceRiskEvent` table |
| OWASP ASVS **2.7** | OTP Verification | No MFA on enrollment | `DeviceMFAChallenge` (TOTP + Email OTP) |
| OWASP ASVS **2.2** | General Authenticator | No expiry | `expires_at` + `revalidation_required` |
| OWASP ASVS **6.4** | Secret Management | Plaintext JSON | DB storage; OTP stored as salted hash only |
| OWASP ASVS **7.2** | Log Processing | No SIEM fields | `siem_metadata` JSONField on access logs |
| **Zero Trust** | Re-evaluate per request | Cache may persist stale state | DB lookup every request; no implicit trust |

---

## 25. Deployment & Migration Plan

### Phase 0 — Prerequisites (Day 1)

```bash
# Install new dependencies
pip install pyotp qrcode[pil]
echo "pyotp>=2.9.0" >> requirements.txt
echo "qrcode[pil]>=7.4" >> requirements.txt

# Generate Django migrations for new models
python manage.py makemigrations core --name=enterprise_device_auth
python manage.py migrate
```

### Phase 1 — Parallel Operation (Week 1)

Run both middleware stacks simultaneously. The new middleware is INACTIVE; v1 legacy middleware remains the enforcer.

```python
# settings.py — Phase 1: v1 active, v2 shadow mode
MIDDLEWARE = [
    ...
    'core.middleware.device_authorization.DeviceAuthorizationMiddleware',  # v1 ACTIVE
    # 'core.device.middleware.DeviceAuthMiddleware',                       # v2 disabled
    ...
]
```

Seed the new DB tables from the existing JSON:
```bash
python manage.py shell < core/device/migration_seed.py
# Or with dry-run first:
python core/device/migration_seed.py --dry-run
```

### Phase 2 — Migrate Users to New Enrollment Flow (Week 2)

1. Deploy the updated `/admin/device/request-authorization/` view that:
   - Uses `DeviceService.enroll_device()` instead of `DeviceAuthorizationRequest`
   - Presents TOTP setup / Email OTP MFA gate
2. New enrollments go through v2 flow; existing v1 approvals remain valid
3. Run access log comparison: v1 vs v2 decisions should match for all existing devices

### Phase 3 — Cutover (Week 3)

```python
# settings.py — Phase 3: v2 active, v1 retained but disabled
MIDDLEWARE = [
    ...
    # 'core.middleware.device_authorization.DeviceAuthorizationMiddleware',  # v1 DISABLED
    'core.device.middleware.DeviceAuthMiddleware',                           # v2 ACTIVE
    ...
]
```

Verify:
- All known authorized devices pass in v2
- Armory terminal active-hours restriction working
- MFA enrollment flow complete to end

### Phase 4 — Legacy Cleanup (Week 4+)

- Remove `core/middleware/device_authorization.py` (legacy v1)
- Remove `admin/device_auth_models.py` (replaced by `core/device/models.py`)
- Archive `authorized_devices.json` to read-only
- Enable DB-backed transaction counters (remove cache dependency)
- Schedule `revalidation_required=True` for all devices enrolled > 90 days ago

### Phase 5 — Advanced Features (Next Sprint)

- Activate mTLS client certificates (`MTLS_ENABLED = True`)
- Deploy `purge_device_logs` management command on cron
- Wire `DeviceRiskEvent.acknowledged=False` count into admin dashboard widget
- Implement Two-Factor Device Approval for MILITARY tier (four-eyes)
- Add CIDR-based IP range binding as alternative to exact-IP binding

---

## Appendix A: Current v1 Authorized Devices Summary

| Device | IP | Security Level | Transactions | Active Hours | Notes |
|--------|-----|---------------|-------------|-------------|-------|
| Localhost Development | 127.0.0.1 | DEVELOPMENT | 1000/day | Unrestricted | Dev only |
| Developer PC | 192.168.0.82 | HIGH_SECURITY | 100/day | Unrestricted | No fingerprint in JSON |
| Armory PC Terminal | 192.168.0.100 | MILITARY | 200/day | 06:00–18:00 | Bug fixed in v1; no fingerprint |

> All three devices will be seeded into `AuthorizedDevice` via `migration_seed.py` during Phase 1.  
> The Armory PC Terminal will receive a new server-issued `device_token` and MFA will be required on next re-enrollment.

---

## Appendix B: File Index — New Implementation

```
armguard/core/device/
├── __init__.py           Module marker
├── models.py             AuthorizedDevice, DeviceAuditEvent, DeviceMFAChallenge,
│                         DeviceAccessLog, DeviceRiskEvent
├── service.py            DeviceService (facade), PathSecurityResolver,
│                         DeviceIdentityService, DeviceRiskEvaluator,
│                         AuthorizationDecisionEngine, AuthDecision
├── mfa.py                TOTPService, EmailOTPService, MFAReadinessCheck
├── middleware.py         DeviceAuthMiddleware (thin adapter)
├── migration_seed.py     One-time data migration from authorized_devices.json
└── tests.py              40+ unit, integration, and penetration tests
```

---

*End of ARMGUARD RDS Device Authorization Security Review & Enterprise Redesign*  
*Commit this document alongside the implementation in `core/device/`.*
