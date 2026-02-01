import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from qr_manager.models import QRCodeImage
from personnel.models import Personnel
from inventory.models import Item
from django.test import RequestFactory
from transactions.views import verify_qr_code
from django.http import QueryDict

print("=" * 80)
print("TESTING QR CODE TRANSACTION FLOW")
print("=" * 80)

# Test 1: Check QR code format in database
print("\n1. CHECKING QR CODE FORMAT IN DATABASE")
qr = QRCodeImage.objects.filter(qr_type='personnel').first()
if qr:
    print(f"   Sample QR Code:")
    print(f"   - reference_id: {qr.reference_id}")
    print(f"   - qr_data: {qr.qr_data}")
    print(f"   - qr_type: {qr.qr_type}")
    print(f"   - is_active: {qr.is_active}")

# Test 2: Check if personnel with that ID exists
print("\n2. CHECKING PERSONNEL RECORD")
test_id = "PE-987703210126"
try:
    personnel = Personnel.objects.get(id=test_id)
    print(f"   ✅ Personnel found: {personnel.get_full_name()}")
    print(f"   - ID: {personnel.id}")
    print(f"   - Status: {personnel.status}")
    print(f"   - deleted_at: {personnel.deleted_at}")
except Personnel.DoesNotExist:
    print(f"   ❌ Personnel NOT FOUND with id={test_id}")
    print(f"\n   All active personnel IDs:")
    for p in Personnel.objects.all()[:5]:
        print(f"     - {p.id}")

# Test 3: Simulate the verify_qr_code view logic
print("\n3. SIMULATING verify_qr_code VIEW")

test_cases = [
    ("Direct ID (what user typed)", "PE-987703210126"),
    ("Full QR format", "PERSONNEL:PE-987703210126:SGT Maceda, Milchur Angelo:987703"),
]

for name, qr_data in test_cases:
    print(f"\n   Test: {name}")
    print(f"   Input: {qr_data}")
    
    # Parse QR code data (copied from views.py)
    personnel_id = None
    item_id = None
    
    if qr_data.startswith('PERSONNEL:'):
        parts = qr_data.split(':')
        if len(parts) >= 2:
            personnel_id = parts[1]
            print(f"   Parsed as PERSONNEL, extracted ID: {personnel_id}")
    elif qr_data.startswith('ITEM:'):
        parts = qr_data.split(':')
        if len(parts) >= 2:
            item_id = parts[1]
            print(f"   Parsed as ITEM, extracted ID: {item_id}")
    else:
        # Legacy format
        if qr_data.startswith('PE-') or qr_data.startswith('PO-'):
            personnel_id = qr_data
            print(f"   Parsed as legacy PERSONNEL ID: {personnel_id}")
        elif qr_data.startswith('ITM-'):
            item_id = qr_data
            print(f"   Parsed as legacy ITEM ID: {item_id}")
    
    if personnel_id:
        print(f"   Looking up QR code: qr_type='personnel', reference_id='{personnel_id}'")
        try:
            qr_code = QRCodeImage.objects.get(qr_type='personnel', reference_id=personnel_id)
            print(f"   ✅ QR code found")
            
            # Validate
            is_valid, message = qr_code.is_valid_for_transaction()
            print(f"   Validation: {is_valid}, Message: {message}")
            
            if is_valid:
                # Get personnel
                print(f"   Looking up personnel: id='{personnel_id}'")
                try:
                    personnel = Personnel.objects.get(id=personnel_id)
                    print(f"   ✅ SUCCESS: Personnel found: {personnel.get_full_name()}")
                except Personnel.DoesNotExist:
                    print(f"   ❌ FAIL: Personnel.DoesNotExist")
        except QRCodeImage.DoesNotExist:
            print(f"   ❌ FAIL: QR code not found in system")

# Test 4: Test with actual Django request
print("\n4. TESTING WITH ACTUAL DJANGO REQUEST")
factory = RequestFactory()
request = factory.post('/transactions/verify_qr/', {'qr_data': 'PE-987703210126'})
request.user = None  # Anonymous for test

try:
    response = verify_qr_code(request)
    import json
    result = json.loads(response.content)
    print(f"   Response: {result}")
    if result.get('success'):
        print(f"   ✅ SUCCESS")
    else:
        print(f"   ❌ FAIL: {result.get('error')}")
except Exception as e:
    print(f"   ❌ EXCEPTION: {str(e)}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
