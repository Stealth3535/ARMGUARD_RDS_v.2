# Soft Delete System - Quick Reference

## For Developers

### Querying Personnel

```python
# Get active personnel only (default - shown in GUI)
active = Personnel.objects.all()

# Get ALL personnel including deleted
all_personnel = Personnel.all_objects.all()

# Get only deleted personnel
deleted = Personnel.all_objects.filter(deleted_at__isnull=False)
```

### Querying QR Codes

```python
# Get active QR codes only (default - shown in GUI)
active_qrs = QRCodeImage.objects.all()

# Get ALL QR codes including inactive
all_qrs = QRCodeImage.all_objects.all()

# Get only inactive QR codes
inactive_qrs = QRCodeImage.all_objects.filter(is_active=False)
```

### Deleting Personnel

```python
# Soft delete (recommended - keeps records for audit)
personnel.soft_delete()

# Hard delete (NOT recommended - permanently removes from database)
personnel.delete()
```

### Validating QR Codes for Transactions

```python
qr_code = QRCodeImage.objects.get(reference_id=data)
is_valid, message = qr_code.is_valid_for_transaction()

if not is_valid:
    # Handle invalid QR code
    return JsonResponse({'success': False, 'error': message})
```

### Reactivating Soft-Deleted Records (if needed in future)

```python
# Reactivate personnel
personnel = Personnel.all_objects.get(id='PE-123456')
personnel.deleted_at = None
personnel.status = Personnel.STATUS_ACTIVE
personnel.save()

# Reactivate QR code
qr_code = QRCodeImage.all_objects.get(reference_id='PE-123456')
qr_code.reactivate()
```

## For System Administrators

### Checking Deleted Records

```bash
# Run verification script
python test_final_verification.py

# Check QR code status
python check_qr_status.py

# Look for orphaned QR codes
python cleanup_orphaned_files.py
```

### Cleaning Up Test Data

```bash
# Clean up test personnel and QR codes
python cleanup_test_data.py
```

### Database Queries

```sql
-- Count active vs deleted personnel
SELECT 
  COUNT(*) FILTER (WHERE deleted_at IS NULL) as active,
  COUNT(*) FILTER (WHERE deleted_at IS NOT NULL) as deleted,
  COUNT(*) as total
FROM personnel;

-- List deleted personnel
SELECT id, surname, firstname, serial, deleted_at
FROM personnel
WHERE deleted_at IS NOT NULL;

-- Count active vs inactive QR codes
SELECT 
  COUNT(*) FILTER (WHERE is_active = 1) as active,
  COUNT(*) FILTER (WHERE is_active = 0) as inactive,
  COUNT(*) as total
FROM qr_codes
WHERE qr_type = 'personnel';
```

## Expected Behavior

### When Deleting a User
1. User record is deleted from database
2. Linked personnel is automatically soft-deleted (via signal)
3. Personnel record remains in database with `deleted_at` timestamp
4. Personnel status changes to 'Inactive'
5. Associated QR code is deactivated
6. Personnel disappears from GUI lists
7. QR code disappears from GUI lists
8. QR code cannot be used for transactions

### When Deleting Personnel Directly
1. Personnel is soft-deleted (not removed from database)
2. `deleted_at` timestamp is set
3. Status changes to 'Inactive'
4. Associated QR code is deactivated
5. Record remains in database for audit
6. Hidden from default GUI queries
7. QR code cannot be used for transactions

### GUI Behavior
- **Personnel List**: Only shows active personnel
- **QR Code List**: Only shows active QR codes
- **Print QR Codes**: Only prints active QR codes
- **Transactions**: Rejects inactive QR codes with error message

### Database Behavior
- Deleted records remain in database indefinitely
- Can be accessed using `all_objects` manager
- Useful for audit trails and historical reporting
- No automatic cleanup/archival (by design)

## Troubleshooting

### Issue: Deleted personnel still showing in GUI
**Check**:
```python
p = Personnel.objects.get(id='PE-123456')  # Should raise DoesNotExist
p = Personnel.all_objects.get(id='PE-123456')  # Should work
print(p.deleted_at)  # Should show timestamp
```

### Issue: QR code still usable after deletion
**Check**:
```python
qr = QRCodeImage.all_objects.get(reference_id='PE-123456')
print(qr.is_active)  # Should be False
is_valid, msg = qr.is_valid_for_transaction()
print(is_valid, msg)  # Should be False, with error message
```

### Issue: Orphaned QR codes
**Fix**:
```bash
python check_qr_status.py  # Identify orphans
python cleanup_orphaned_files.py  # Clean up
```

### Issue: Cannot create personnel with same serial as deleted one
**Explanation**: Personnel IDs are generated as `PE-{serial}{date}`. If you create two personnel with the same serial on the same day, they'll have the same ID, causing a conflict.

**Solutions**:
1. Use different serial numbers
2. Hard delete test personnel: `Personnel.all_objects.filter(serial='TEST').delete()`
3. Wait until next day to reuse serial number
4. Manually set different ID: `personnel.id = 'PE-TEST-001'` before save

## Testing

### Before Production Deployment
```bash
# 1. Run comprehensive tests
python test_delete_workflow.py
python test_final_verification.py

# 2. Check for issues
python check_qr_status.py

# 3. Verify in browser
# - Create test personnel
# - Delete test personnel
# - Verify hidden from lists
# - Try to use QR code in transaction (should fail)
# - Check database to confirm record still exists

# 4. Clean up test data
python cleanup_test_data.py
```

## Summary

✅ **Soft delete is working perfectly**
- Deleted personnel hidden from GUI
- Deleted QR codes hidden from GUI
- Records kept in database for audit
- Transaction validation prevents use of deleted QR codes
- Automatic cascade from user deletion to personnel deletion

🔒 **Security**
- Inactive QR codes cannot be used
- Clear error messages for users
- All changes logged with timestamps

📊 **Audit Trail**
- All deleted records retained
- Accessible via `all_objects` manager
- Timestamps for all deletions
- Status changes tracked
