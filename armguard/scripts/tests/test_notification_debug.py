"""
Debug script to test notification display in browser
Creates a test transaction and shows debug info
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from personnel.models import Personnel
from inventory.models import Item
from transactions.models import Transaction
from django.utils import timezone

print("=" * 70)
print("NOTIFICATION DEBUG TEST")
print("=" * 70)

# Get test data
personnel = Personnel.objects.filter(deleted_at__isnull=True).first()
item = Item.objects.filter(status='Available').first()

if personnel and item:
    print(f"\n✓ Personnel: {personnel.get_full_name()} (ID: {personnel.id})")
    print(f"✓ Item: {item.item_type} - {item.serial} (ID: {item.id})")
    
    # Create a test transaction
    transaction = Transaction.objects.create(
        personnel=personnel,
        item=item,
        action='Take',
        mags=2,
        rounds=30,
        duty_type='Debug Test',
        notes='Testing notification system',
        date_time=timezone.now()
    )
    
    print(f"\n✓ Transaction #{transaction.id} created successfully!")
    print(f"  Action: {transaction.action}")
    print(f"  Time: {transaction.date_time}")
    
    # Now check the template
    print("\n" + "=" * 70)
    print("TEMPLATE CHECK")
    print("=" * 70)
    
    with open('transactions/templates/transactions/qr_scanner.html', 'r', encoding='utf-8') as f:
        content = f.read()
        
        # Find the messages block
        if '{% if messages %}' in content:
            print("\n✓ Messages block found in template")
            
            # Check for specific styling
            if 'position: fixed' in content:
                print("✓ Floating position style present")
            else:
                print("✗ Missing floating position style")
                
            if 'alert-dismissible' in content:
                print("✓ Dismissible alert classes present")
            else:
                print("✗ Missing dismissible classes")
                
            if 'bootstrap.Alert' in content:
                print("✓ Bootstrap Alert JavaScript present")
            else:
                print("✗ Missing Bootstrap Alert JS")
                
            if '@keyframes slideIn' in content:
                print("✓ SlideIn animation defined")
            else:
                print("✗ Missing slideIn animation")
        else:
            print("\n✗ No messages block found!")
    
    # Check base template for Bootstrap
    print("\n" + "=" * 70)
    print("BOOTSTRAP CHECK")
    print("=" * 70)
    
    base_template_paths = [
        'core/templates/base.html',
        'templates/base.html',
    ]
    
    for base_path in base_template_paths:
        if os.path.exists(base_path):
            with open(base_path, 'r', encoding='utf-8') as f:
                base_content = f.read()
                
                if 'bootstrap' in base_content.lower():
                    print(f"\n✓ Bootstrap found in {base_path}")
                    
                    if 'bootstrap.min.js' in base_content or 'bootstrap.bundle' in base_content:
                        print("✓ Bootstrap JavaScript included")
                    else:
                        print("⚠ Bootstrap CSS found but JS might be missing")
                else:
                    print(f"\n⚠ Bootstrap not found in {base_path}")
            break
    
    print("\n" + "=" * 70)
    print("MANUAL TEST INSTRUCTIONS")
    print("=" * 70)
    print("""
To test notifications manually:

1. Go to: http://192.168.59.138:8000/transactions/qr-scanner/

2. Open browser Developer Tools (F12)
   - Go to Console tab
   - Check for any JavaScript errors (red text)

3. Scan personnel and item QR codes

4. Submit the transaction form

5. After page reloads, check:
   - Look for floating alert in top-right corner
   - Check Console for any errors
   - Check Network tab - look for the POST request
   
6. If no notification appears, run this in browser Console:
   
   document.querySelectorAll('.alert').forEach(el => {
       console.log('Alert found:', el.textContent, el.style.cssText);
   });
   
   This will show if alerts exist but are invisible.

7. Also check if messages middleware is working:
   - Look at page source (Ctrl+U)
   - Search for "{% if messages %}" or "alert alert-"
   - If you see raw Django tags, templates aren't being rendered
""")
    
else:
    print("\n✗ No test data available")
    print("  Need active personnel and available items")
