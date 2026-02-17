"""
Update M4 item to use existing factory QR code as primary key
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from inventory.models import Item
from transactions.models import Transaction
from qr_manager.models import QRCodeImage
from django.db import transaction as db_transaction

print("=" * 70)
print("UPDATE M4 TO USE FACTORY QR CODE")
print("=" * 70)

# The current M4 ID and the new QR code from scan
OLD_ID = "IR-PAF20244759120226"
NEW_ID = "DASANPAF202447592024.10.02P5137"  # Scanned QR code

print(f"\nOld ID: {OLD_ID}")
print(f"New ID (Scanned QR): {NEW_ID}")

try:
    # Find the M4 item
    m4_item = Item.objects.get(id=OLD_ID)
    print(f"\n✓ Found M4: {m4_item.item_type} - {m4_item.serial}")
    print(f"  Current Status: {m4_item.status}")
    print(f"  Current Condition: {m4_item.condition}")
    
    # Check for any transactions using this item
    transactions = Transaction.objects.filter(item_id=OLD_ID)
    transaction_count = transactions.count()
    print(f"\n  Transactions found: {transaction_count}")
    
    # Check for QR code record
    try:
        qr_code_obj = QRCodeImage.objects.get(qr_type='item', reference_id=OLD_ID)
        print(f"  QR Code record found: {qr_code_obj.id}")
        has_qr_record = True
    except QRCodeImage.DoesNotExist:
        print("  No QR Code record found")
        has_qr_record = False
    
    # Confirm before proceeding
    print("\n" + "=" * 70)
    print("PROPOSED CHANGES:")
    print("=" * 70)
    print(f"1. Change item ID from {OLD_ID} to {NEW_ID}")
    print(f"2. Update qr_code field to {NEW_ID}")
    if transaction_count > 0:
        print(f"3. Update {transaction_count} transaction(s) to reference new ID")
    if has_qr_record:
        print(f"4. Update QR code record reference_id to {NEW_ID}")
    
    print("\n⚠️  WARNING: This will change the primary key!")
    response = input("\nProceed with update? (yes/no): ")
    
    if response.lower() != 'yes':
        print("\n❌ Update cancelled.")
        exit(0)
    
    # Perform the update in a transaction
    with db_transaction.atomic():
        print("\n🔄 Starting update...")
        
        # Step 1: Update all transactions to point to new ID
        if transaction_count > 0:
            print(f"\n  Updating {transaction_count} transaction(s)...")
            for trans in transactions:
                trans.item_id = NEW_ID
                trans.save(update_fields=['item_id'])
            print(f"  ✓ Transactions updated")
        
        # Step 2: Update QR code record
        if has_qr_record:
            print("\n  Updating QR code record...")
            qr_code_obj.reference_id = NEW_ID
            qr_code_obj.save(update_fields=['reference_id'])
            print("  ✓ QR code record updated")
        
        # Step 3: Save old item data before deletion
        print("\n  Saving item data...")
        item_data = {
            'item_type': m4_item.item_type,
            'serial': m4_item.serial,
            'description': m4_item.description,
            'condition': m4_item.condition,
            'status': m4_item.status,
            'registration_date': m4_item.registration_date,
            'created_at': m4_item.created_at,
            'updated_at': m4_item.updated_at
        }
        print("  ✓ Item data saved")
        
        # Step 4: Delete old item first (to free up the unique serial)
        print("\n  Removing old item record...")
        m4_item.delete()
        print("  ✓ Old item deleted")
        
        # Step 5: Create new item with new ID
        print("\n  Creating new item record with factory QR code...")
        new_item = Item(
            id=NEW_ID,
            item_type=item_data['item_type'],
            serial=item_data['serial'],
            description=item_data['description'],
            condition=item_data['condition'],
            status=item_data['status'],
            registration_date=item_data['registration_date'],
            qr_code=NEW_ID,
            created_at=item_data['created_at'],
            updated_at=item_data['updated_at']
        )
        new_item.save()
        print("  ✓ New item created")
    
    print("\n" + "=" * 70)
    print("✅ UPDATE COMPLETE!")
    print("=" * 70)
    
    # Verify the update
    print("\n🔍 Verifying update...")
    updated_item = Item.objects.get(id=NEW_ID)
    print(f"\n  Item ID: {updated_item.id}")
    print(f"  Item Type: {updated_item.item_type}")
    print(f"  Serial: {updated_item.serial}")
    print(f"  QR Code: {updated_item.qr_code}")
    print(f"  Status: {updated_item.status}")
    
    if transaction_count > 0:
        verify_trans = Transaction.objects.filter(item_id=NEW_ID).count()
        print(f"\n  Transactions with new ID: {verify_trans}")
    
    print("\n✓ M4 now uses factory QR code as primary key!")
    print("✓ All related records have been updated.")
    
except Item.DoesNotExist:
    print(f"\n❌ Error: M4 item with ID {OLD_ID} not found!")
    print("\nCurrent items in database:")
    for item in Item.objects.all():
        print(f"  - {item.id}: {item.item_type} {item.serial}")
    
except Exception as e:
    print(f"\n❌ Error during update: {str(e)}")
    import traceback
    traceback.print_exc()
    print("\n⚠️  Update rolled back. No changes made.")

print("\n" + "=" * 70)
