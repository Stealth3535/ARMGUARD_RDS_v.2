# ArmGuard Security Audit Report
**Date:** November 8, 2025  
**Auditor:** Comprehensive Code Review & Security Analysis  
**Application:** ArmGuard v1.0 (Django 5.1.1)

---

## Executive Summary

A thorough security audit was conducted on the ArmGuard application, examining all code, configurations, and deployment scripts. The application demonstrates **strong security foundations** with proper implementation of Django security features, but several **CRITICAL issues** require immediate attention before production deployment.

### Risk Assessment
- **Critical Issues:** 3
- **High Priority:** 4
- **Medium Priority:** 2
- **Low Priority:** 3
- **Best Practices:** 5

---

## ✅ STRENGTHS IDENTIFIED

### 1. Authentication & Authorization ✓
- **Proper use of @login_required decorators** on all sensitive views
- **Role-based access control** implemented with Django Groups (Admin, Armorer, Personnel)
- **@user_passes_test** correctly used for admin-only views
- **Django Axes** (v8.0.0) configured for brute-force protection (5 attempts, 1-hour lockout)
- **Strong password validation** (12 characters minimum in production)

### 2. Input Validation ✓
- **No raw SQL queries** - All database queries use Django ORM
- **No .raw() or cursor.execute()** - Safe from SQL injection
- **Form validation** properly implemented with Django forms
- **RegexValidator** for phone numbers (+639XXXXXXXXX format)
- **Model-level validation** in save() methods

### 3. XSS Prevention ✓
- **No {{ var|safe }}** usage in templates - All output is properly escaped
- **No mark_safe()** calls in Python code
- **Django's auto-escaping** enabled by default

### 4. Security Middleware ✓
- Proper middleware order (SecurityMiddleware first)
- **Django Axes middleware** for failed login tracking
- **Custom RateLimitMiddleware** (60 req/min per IP)
- **SecurityHeadersMiddleware** (Permissions-Policy, Expect-CT)
- **StripSensitiveHeadersMiddleware** removes X-Powered-By headers

### 5. Session Security ✓
- SESSION_COOKIE_HTTPONLY = True
- SESSION_COOKIE_SAMESITE = 'Lax'
- CSRF_COOKIE_HTTPONLY = True
- Session timeout configured (1 hour in production)

---

## 🚨 CRITICAL ISSUES (Fix Immediately)

### 1. **API Endpoints Have @csrf_exempt - SEVERE VULNERABILITY**

**File:** `core/api_views.py`  
**Line:** 54  
**Severity:** 🔴 **CRITICAL**

```python
@require_http_methods(["POST"])
@csrf_exempt  # ❌ CRITICAL: Removes CSRF protection!
def create_transaction(request):
```

**Risk:**
- **Cross-Site Request Forgery (CSRF)** attacks possible
- Malicious websites can submit transactions on behalf of authenticated users
- No authentication check - ANYONE can create transactions!

**Impact:**
- Attackers can forge transactions (Take/Return items)
- Unauthorized access to API endpoints
- Data integrity compromise

**Fix Required:**
```python
# REMOVE @csrf_exempt
# ADD authentication check
from django.contrib.auth.decorators import login_required

@require_http_methods(["POST"])
@login_required  # ✓ Require authentication
def create_transaction(request):
    # CSRF protection is now enabled
```

---

### 2. **Debug Print Statements in Production Code**

**File:** `admin/views.py`  
**Lines:** 350-354  
**Severity:** 🔴 **CRITICAL**

```python
# Debug: print to console
print(f"DEBUG: Editing user {edit_user_obj.username}")
print(f"DEBUG: Personnel found: {personnel.id}")
print(f"DEBUG: Initial data: {initial_data}")
```

**Risk:**
- Sensitive information logged to console/logs
- Usernames and IDs exposed in production logs
- Performance impact from unnecessary I/O

**Fix Required:**
```python
# Use Django logging instead
import logging
logger = logging.getLogger(__name__)

# Replace print() with logger.debug()
logger.debug(f"Editing user {edit_user_obj.username}")
logger.debug(f"Personnel found: {personnel.id}")
```

---

### 3. **Missing Authentication on API GET Endpoints**

**File:** `core/api_views.py`  
**Lines:** 17, 30  
**Severity:** 🔴 **CRITICAL**

```python
@require_http_methods(["GET"])
def get_personnel(request, personnel_id):
    # ❌ NO authentication required!
    # Anyone can query personnel data
```

**Risk:**
- **Information disclosure** - Unauthenticated users can access personnel data
- **Enumeration attacks** - Attackers can iterate through IDs to extract all personnel
- PII exposure (names, ranks, phone numbers, photos)

**Fix Required:**
```python
from django.contrib.auth.decorators import login_required

@require_http_methods(["GET"])
@login_required  # ✓ Require authentication
def get_personnel(request, personnel_id):
```

---

## 🔴 HIGH PRIORITY ISSUES

### 4. **File Upload Validation Missing**

**File:** `personnel/models.py`, `qr_manager/models.py`  
**Severity:** 🟠 **HIGH**

```python
picture = models.ImageField(upload_to='personnel/pictures/', blank=True, null=True)
# ❌ No file type validation
# ❌ No file size validation
```

**Risk:**
- **Malicious file upload** (PHP shells, executables disguised as images)
- **Path traversal** via filename manipulation
- **Storage exhaustion** (large file uploads)

**Fix Required:**
```python
from django.core.validators import FileExtensionValidator

picture = models.ImageField(
    upload_to='personnel/pictures/',
    blank=True,
    null=True,
    validators=[
        FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'gif']),
    ]
)

# Add in forms.py:
def clean_picture(self):
    picture = self.cleaned_data.get('picture')
    if picture:
        # Validate file size (5MB max)
        if picture.size > 5 * 1024 * 1024:
            raise ValidationError('Image file too large (max 5MB)')
        # Validate image content
        try:
            img = Image.open(picture)
            img.verify()
        except Exception:
            raise ValidationError('Invalid image file')
    return picture
```

---

### 5. **Insecure Default SECRET_KEY**

**File:** `core/settings.py`  
**Line:** 24  
**Severity:** 🟠 **HIGH**

```python
SECRET_KEY = config('DJANGO_SECRET_KEY', default='django-insecure-change-this-key')
```

**Risk:**
- **Insecure default** used if .env file is missing
- Session hijacking, CSRF token forgery
- Production deployments may accidentally use default key

**Fix Required:**
```python
# Force requirement in production
SECRET_KEY = config('DJANGO_SECRET_KEY')  # No default - will fail if missing

# In .env.example, add generation instructions:
# Generate with: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

---

### 6. **Missing Rate Limiting on Login**

**File:** `core/urls.py`  
**Line:** 18  
**Severity:** 🟠 **HIGH**

```python
path('login/', auth_views.LoginView.as_view(template_name='auth/login.html'), name='login'),
# ❌ No rate limiting decorator
```

**Risk:**
- **Credential stuffing attacks** (despite Django Axes)
- **DoS attacks** on login endpoint
- High server load from brute-force attempts

**Fix Required:**
```python
# Create custom login view with rate limiting
from django_ratelimit.decorators import ratelimit

@ratelimit(key='ip', rate='5/m', method='POST')
def custom_login(request):
    if getattr(request, 'limited', False):
        messages.error(request, 'Too many login attempts. Try again later.')
        return redirect('login')
    return auth_views.LoginView.as_view(template_name='auth/login.html')(request)

# Update urls.py:
path('login/', custom_login, name='login'),
```

---

### 7. **QR Code Path Traversal Risk**

**File:** `qr_manager/models.py`  
**Line:** 10  
**Severity:** 🟠 **HIGH**

```python
def qr_upload_path(instance, filename):
    # ❌ filename not sanitized - potential path traversal
    if instance.qr_type == 'item':
        return f'qr_codes/items/{filename}'
```

**Risk:**
- **Path traversal attack** via malicious filename (`../../../etc/passwd`)
- Files written outside intended directory

**Fix Required:**
```python
import os
from django.utils.text import get_valid_filename

def qr_upload_path(instance, filename):
    # Sanitize filename to prevent path traversal
    safe_filename = get_valid_filename(os.path.basename(filename))
    if instance.qr_type == 'item':
        return f'qr_codes/items/{safe_filename}'
    else:
        return f'qr_codes/{instance.qr_type}/{safe_filename}'
```

---

## 🟡 MEDIUM PRIORITY ISSUES

### 8. **Verbose Error Messages in API**

**File:** `core/api_views.py`  
**Line:** 101  
**Severity:** 🟡 **MEDIUM**

```python
except Exception as e:
    return JsonResponse({'error': str(e)}, status=500)
    # ❌ Exposes internal error details
```

**Risk:**
- **Information disclosure** (stack traces, database structure)
- Helps attackers understand internal workings

**Fix Required:**
```python
except Exception as e:
    logger.error(f"Transaction creation failed: {str(e)}")
    return JsonResponse({'error': 'Internal server error'}, status=500)
```

---

### 9. **Missing Content-Type Validation in API**

**File:** `core/api_views.py`  
**Severity:** 🟡 **MEDIUM**

**Risk:**
- API accepts any content type
- Potential for content-type confusion attacks

**Fix Required:**
```python
@require_http_methods(["POST"])
@login_required
def create_transaction(request):
    # Validate Content-Type
    if request.content_type != 'application/json':
        return JsonResponse({'error': 'Content-Type must be application/json'}, status=415)
```

---

## ⚠️ LOW PRIORITY ISSUES

### 10. **No Admin IP Whitelist**

**File:** `core/middleware.py`  
**Severity:** 🟢 **LOW**

**Observation:** AdminIPWhitelistMiddleware exists but not enabled in MIDDLEWARE

**Recommendation:**
```python
# Add to settings.py MIDDLEWARE (optional for extra security)
'core.middleware.AdminIPWhitelistMiddleware',

# Configure in .env:
ADMIN_ALLOWED_IPS=192.168.1.100,10.0.0.50
```

---

### 11. **Missing HTTP Security Headers**

**File:** `core/settings_production.py`  
**Severity:** 🟢 **LOW**

**Missing Headers:**
- Content-Security-Policy (CSP)
- Referrer-Policy
- X-Content-Type-Options

**Fix:** Already partially implemented, but CSP is commented as "basic"

---

### 12. **Transaction Business Logic Validation**

**File:** `transactions/models.py`  
**Severity:** 🟢 **LOW**

**Enhancement:**
```python
def save(self, *args, **kwargs):
    # Add validation: Can't return item that's not issued
    if self.action == self.ACTION_RETURN:
        if self.item.status != Item.STATUS_ISSUED:
            raise ValueError("Cannot return item that is not currently issued")
    
    # Add validation: Can't take item that's already issued
    if self.action == self.ACTION_TAKE:
        if self.item.status == Item.STATUS_ISSUED:
            raise ValueError("Item is already issued")
```

---

## 📋 BEST PRACTICES & RECOMMENDATIONS

### 1. **Logging Enhancement**
- Replace all `print()` statements with `logging`
- Separate security logs from application logs
- Implement log rotation (already done in production settings)

### 2. **Environment Variables**
- Create `.env` file from `.env.example`
- Never commit `.env` to Git (already in .gitignore ✓)
- Use strong secrets in production

### 3. **Django Deployment Checklist**
Django check --deploy identified 5 warnings (expected for development):
- DEBUG=True (set to False in production ✓)
- SECURE_SSL_REDIRECT (enabled in production settings ✓)
- SESSION_COOKIE_SECURE (enabled in production settings ✓)
- CSRF_COOKIE_SECURE (enabled in production settings ✓)
- SECURE_HSTS_SECONDS (31536000 in production ✓)

### 4. **Database Security**
- Use PostgreSQL in production (supported in settings ✓)
- Regular backups
- Database credentials in .env only

### 5. **Dependency Updates**
```bash
# Check for security vulnerabilities
pip install safety
safety check

# Update dependencies regularly
pip list --outdated
```

---

## 🔧 IMMEDIATE ACTION ITEMS

### Priority 1 (Fix Today)
1. ✅ Remove @csrf_exempt from API endpoints
2. ✅ Add @login_required to all API views
3. ✅ Replace print() statements with logging
4. ✅ Add file upload validation

### Priority 2 (Fix This Week)
5. ✅ Remove default SECRET_KEY
6. ✅ Add rate limiting to login
7. ✅ Sanitize QR code filenames
8. ✅ Sanitize API error messages

### Priority 3 (Before Production)
9. ✅ Add Content-Type validation to API
10. ✅ Implement transaction business logic validation
11. ✅ Review and test all security settings
12. ✅ Run penetration testing

---

## 📊 COMPLIANCE STATUS

| Security Category | Status | Notes |
|-------------------|--------|-------|
| Authentication | ✅ PASS | Django Axes, strong passwords |
| Authorization | ✅ PASS | Proper decorators, role-based |
| SQL Injection | ✅ PASS | No raw SQL, Django ORM only |
| XSS Prevention | ✅ PASS | Auto-escaping, no mark_safe |
| CSRF Protection | ❌ FAIL | @csrf_exempt on API (CRITICAL) |
| Session Security | ✅ PASS | HttpOnly, Secure flags |
| File Uploads | ⚠️ PARTIAL | Missing validation |
| API Security | ❌ FAIL | No authentication (CRITICAL) |
| Error Handling | ⚠️ PARTIAL | Verbose errors in API |
| Logging | ⚠️ PARTIAL | print() instead of logging |

---

## 🎯 CONCLUSION

**Overall Assessment:** The ArmGuard application has a **solid security foundation** with proper Django security practices, but requires **immediate fixes** to three critical vulnerabilities before production deployment:

1. **API CSRF Protection** - Remove @csrf_exempt
2. **API Authentication** - Add @login_required to all endpoints
3. **Debug Logging** - Remove print() statements

After addressing these critical issues, the application will be **production-ready** with strong security posture.

**Estimated Fix Time:** 2-4 hours for all critical and high-priority issues.

---

## 📝 VERIFICATION CHECKLIST

After applying fixes, verify:
- [ ] Django check --deploy passes with 0 critical issues
- [ ] All API endpoints require authentication
- [ ] CSRF protection enabled on all POST endpoints
- [ ] No print() statements in production code
- [ ] File upload validation working
- [ ] Rate limiting on login tested
- [ ] Security headers present in responses
- [ ] Error messages don't expose internals
- [ ] SECRET_KEY from environment only
- [ ] Logging to files, not console

---

**Report Generated:** November 8, 2025  
**Next Review:** Before production deployment + every 6 months
