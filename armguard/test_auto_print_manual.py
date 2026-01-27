"""
Simple Auto-Print Manual Test
Run this to test the auto-print functionality with an actual transaction
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from transactions.models import Transaction
from django.conf import settings

print("\n" + "="*80)
print("MANUAL AUTO-PRINT TEST")
print("="*80)

# Get the most recent Take transaction
recent_take = Transaction.objects.filter(action='Take').order_by('-date_time').first()

if not recent_take:
    print("✗ No Take transactions found in database")
    sys.exit(1)

print(f"\n✓ Found recent transaction: #{recent_take.id}")
print(f"  Personnel: {recent_take.personnel.get_full_name()}")
print(f"  Item: {recent_take.item.item_type} {recent_take.item.serial}")
print(f"  Date/Time: {recent_take.date_time.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"  Action: {recent_take.action}")

# Check if PDF exists
date_str = recent_take.date_time.strftime('%Y%m%d_%H%M%S')
filename = f"Transaction_{recent_take.id}_{date_str}.pdf"
pdf_path = os.path.join(settings.MEDIA_ROOT, 'transaction_forms', filename)

print(f"\n--- PDF File Check ---")
print(f"Expected path: {pdf_path}")

if os.path.exists(pdf_path):
    file_size = os.path.getsize(pdf_path)
    print(f"✓ PDF exists: {filename}")
    print(f"✓ File size: {file_size:,} bytes")
    
    if file_size > 50000:
        print("\n✅ PDF file is valid")
        print(f"\n📍 To test auto-print:")
        print(f"   1. Go to http://192.168.59.138:8000/transactions/")
        print(f"   2. Create a new WITHDRAW (Take) transaction")
        print(f"   3. The print dialog should appear automatically")
        print(f"   4. Click 'Print' to send to your EPSON L3210")
        print(f"\n📍 Browser console commands to check:")
        print(f"   F12 → Console tab")
        print(f"   Look for: 'Auto-print triggered for transaction XX'")
        print(f"             'PDF loaded, triggering print...'")
        print(f"             'Print triggered successfully'")
        print(f"\n📍 If print doesn't work:")
        print(f"   1. Check browser console for errors")
        print(f"   2. Ensure popup blockers are disabled")
        print(f"   3. Verify EPSON L3210 is set as default printer")
        print(f"   4. Try manually: http://192.168.59.138:8000/print/transaction/{recent_take.id}/pdf/")
    else:
        print(f"\n✗ PDF file too small ({file_size} bytes), likely corrupted")
else:
    print(f"✗ PDF file does not exist")
    print(f"\n💡 This is expected if:")
    print(f"   - Transaction was a Return (no PDF generated)")
    print(f"   - Transaction was created before auto-PDF feature")
    print(f"   - There was an error during PDF generation")

print("\n" + "="*80)
