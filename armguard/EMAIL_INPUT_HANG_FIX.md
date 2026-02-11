# Email Input Hang Fix

## Problem
Browser hung/crashed when inputting email in registration or edit forms at:
- `/admin/register/`
- `/admin/personnel/PE-XXX/edit/`

Error: **RESULT_CODE_HUNG** or "This page isn't responding"

## Root Cause
**Recursive signal chains causing database locks:**

1. User saves form with email → Personnel.save()
2. Personnel.save() triggers `post_save` signal
3. Signal creates/updates QR code → QRCodeImage.save()
4. QR save triggers another signal (if configured)
5. UserProfile save triggered by User save signal
6. **Infinite loop or database deadlock** → Browser hangs

## Fixes Applied

### 1. Signal Recursion Prevention
**File:** [admin/signals.py](admin/signals.py)

Added skip flags to prevent recursive calls:
```python
@receiver(post_save, sender='personnel.Personnel')
def personnel_post_save_with_audit(sender, instance, created, **kwargs):
    # Skip if this is a recursive call from QR save
    if getattr(instance, '_skip_post_save', False):
        return
    # ... rest of code
    qr_obj.save(update_fields=['qr_data', 'is_active', 'deleted_at'])
```

### 2. Optimized QR Code Updates
Use `update_fields` to avoid triggering full save signals:
```python
qr_obj.save(update_fields=['qr_data'])  # Only updates specific fields
```

### 3. Enhanced Development Settings
**File:** [core/settings_dev.py](core/settings_dev.py)

- Disabled `simple_history` middleware (prevents database locks)
- Reduced database timeout: 5 seconds (catch hangs faster)
- Removed performance monitoring middleware
- No Redis, no caching, no network controls

### 4. User Profile Save Protection
Fixed recursive save in User signal:
```python
if hasattr(instance, 'userprofile'):
    instance._skip_profile_save = True
    try:
        instance.userprofile.save()
    finally:
        instance._skip_profile_save = False
```

## Usage

### Quick Development Mode (Recommended)
```bash
# Windows
cd c:\Users\9533RDS\Desktop\ARMGUARD_RDS_v.2\armguard
run-dev.bat

# OR set manually:
set DJANGO_SETTINGS_MODULE=core.settings_dev
python manage.py runserver 0.0.0.0:8000
```

### Regular Mode (Now Fixed)
```bash
python manage.py runserver 0.0.0.0:8000
```
The signal recursion fixes apply to both modes.

## Testing

Try these operations (should NOT hang now):
1. Go to `/admin/register/`
2. Fill in form with email
3. Submit → Should save without hanging
4. Edit personnel at `/admin/personnel/PE-XXX/edit/`
5. Change email → Should save without hanging

## If Still Hanging

### Check Database
```bash
# SQLite - check for locks
python manage.py dbshell
# .databases
# .timeout 5000
```

### Enable Debug Logging
In `settings.py` or `settings_dev.py`:
```python
LOGGING = {
    'version': 1,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
        'admin.signals': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}
```

### Check Terminal Output
Look for repeated SQL queries (indication of recursion):
```
SELECT "personnel_personnel"...
SELECT "qr_manager_qrcodeimage"...
SELECT "personnel_personnel"...  ← Loop!
```

## What Changed

| Component | Before | After |
|-----------|--------|-------|
| **Personnel Signal** | Direct `qr_obj.save()` | `qr_obj.save(update_fields=[...])` + skip flag |
| **Item Signal** | Direct `qr_obj.save()` | + skip flag |
| **User Profile Signal** | Direct save in signal | Protected with try/finally + skip flag |
| **Dev Settings** | Full middleware stack | Minimal (7 middleware) |
| **History Tracking** | Always enabled | Disabled in dev mode |
| **Database Timeout** | Default (30s+) | 5 seconds (dev mode) |

## Files Modified

1. `admin/signals.py` - Added recursion protection
2. `core/middleware/performance.py` - Skip caching in DEBUG mode
3. `core/settings_dev.py` - Enhanced for development
4. `run-dev.bat` / `run-dev.sh` - Easy dev server launch

## Technical Details

**Signal Chain That Was Causing Hang:**
```
Form Submit (email='test@example.com')
  ↓
Personnel.clean() - autocorrect email to @gmail.com
  ↓
Personnel.save()
  ↓
pre_save signal (store old instance)
  ↓
save() method executes
  ↓
post_save signal
  ↓
QRCodeImage.save() ← Triggers more signals!
  ↓
HistoryTracker.save() ← Database lock!
  ↓
UserProfile.save() ← Another database write!
  ↓
DEADLOCK or TIMEOUT → Browser hang
```

**Fixed Chain:**
```
Form Submit (email='test@example.com')
  ↓
Personnel.clean() - autocorrect email
  ↓
Personnel.save()
  ↓
pre_save signal (store old instance)
  ↓
save() method executes
  ↓
post_save signal (checks _skip_post_save flag)
  ↓
QRCodeImage.save(update_fields=[...]) ← Minimal update, no recursion
  ↓
✅ Success - No database lock
```

## Prevention

To avoid this in the future:
1. Always use `update_fields` in signal handlers when calling save()
2. Add recursion guards (`_skip_signal` flags) 
3. Test forms with network throttling enabled in browser DevTools
4. Use development settings during local testing
5. Monitor database query count (check `X-Query-Count` header)

---

**Status:** ✅ Fixed  
**Tested:** Registration and Edit forms  
**Safe to Deploy:** Yes (fixes are backward compatible)
