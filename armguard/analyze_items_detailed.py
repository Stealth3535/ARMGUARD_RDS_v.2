"""
Detailed Item Database Analysis with Transactions
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from inventory.models import Item
from transactions.models import Transaction
from django.db.models import Count, Q
from datetime import datetime, timedelta
from django.utils import timezone

print("=" * 70)
print("DETAILED ITEM DATABASE ANALYSIS")
print("=" * 70)

# Get all items with detailed info
all_items = Item.objects.all().order_by('item_type', 'serial')

print(f"\n📋 COMPLETE ITEM INVENTORY ({all_items.count()} items):")
print("-" * 70)
print(f"{'ID':<25} {'Type':<8} {'Serial':<25} {'Status':<12} {'Condition'}")
print("-" * 70)

for item in all_items:
    print(f"{item.id:<25} {item.item_type:<8} {item.serial:<25} {item.status:<12} {item.condition}")

# Transaction analysis
print("\n" + "=" * 70)
print("TRANSACTION HISTORY ANALYSIS")
print("=" * 70)

total_transactions = Transaction.objects.count()
print(f"\n📊 Total Transactions: {total_transactions}")

if total_transactions > 0:
    # Breakdown by action
    print("\n📤 TRANSACTION ACTIONS:")
    print("-" * 40)
    actions = Transaction.objects.values('action').annotate(count=Count('action'))
    for action in actions:
        print(f"  {action['action']:15} {action['count']}")
    
    # Recent transactions
    print("\n🕒 RECENT TRANSACTIONS (Last 10):")
    print("-" * 70)
    recent = Transaction.objects.select_related('personnel', 'item', 'issued_by').order_by('-date_time')[:10]
    for trans in recent:
        personnel_name = trans.personnel.get_full_name() if trans.personnel else "Unknown"
        item_info = f"{trans.item.item_type} {trans.item.serial}" if trans.item else "Unknown"
        date_str = trans.date_time.strftime("%Y-%m-%d %H:%M")
        print(f"  {date_str} | {trans.action:8} | {personnel_name:20} | {item_info}")
    
    # Items with most transactions
    print("\n🔝 ITEMS WITH MOST ACTIVITY (Top 5):")
    print("-" * 70)
    busy_items = Transaction.objects.values('item__item_type', 'item__serial').annotate(
        count=Count('id')
    ).order_by('-count')[:5]
    
    for idx, item in enumerate(busy_items, 1):
        print(f"  {idx}. {item['item__item_type']} {item['item__serial']}: {item['count']} transactions")
    
    # Personnel with most transactions
    print("\n👤 MOST ACTIVE PERSONNEL (Top 5):")
    print("-" * 70)
    active_personnel = Transaction.objects.values('personnel__firstname', 'personnel__surname', 'personnel__rank').annotate(
        count=Count('id')
    ).order_by('-count')[:5]
    
    for idx, person in enumerate(active_personnel, 1):
        name = f"{person['personnel__rank']} {person['personnel__firstname']} {person['personnel__surname']}"
        print(f"  {idx}. {name}: {person['count']} transactions")
    
    # Check for items currently checked out
    print("\n📤 ITEMS CURRENTLY CHECKED OUT:")
    print("-" * 70)
    
    # Find items with Take actions that don't have matching Return actions
    for item in Item.objects.filter(status='Issued'):
        last_take = Transaction.objects.filter(item=item, action='Take').order_by('-date_time').first()
        if last_take:
            days_out = (timezone.now() - last_take.date_time).days
            personnel = last_take.personnel.get_full_name() if last_take.personnel else "Unknown"
            print(f"  {item.item_type:8} {item.serial:20} → {personnel:25} ({days_out} days)")
    
    if not Item.objects.filter(status='Issued').exists():
        print("  ✓ No items currently checked out")
    
    # Transaction timeline (last 30 days)
    print("\n📈 TRANSACTION TIMELINE (Last 30 Days):")
    print("-" * 70)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    recent_trans = Transaction.objects.filter(date_time__gte=thirty_days_ago).order_by('-date_time')
    
    if recent_trans.exists():
        by_date = {}
        for trans in recent_trans:
            date_key = trans.date_time.strftime("%Y-%m-%d")
            if date_key not in by_date:
                by_date[date_key] = {'Take': 0, 'Return': 0}
            by_date[date_key][trans.action] = by_date[date_key].get(trans.action, 0) + 1
        
        for date_key in sorted(by_date.keys(), reverse=True):
            takes = by_date[date_key].get('Take', 0)
            returns = by_date[date_key].get('Return', 0)
            print(f"  {date_key}: {takes} withdrawals, {returns} returns")
    else:
        print("  No transactions in the last 30 days")

else:
    print("\n  ℹ️  No transactions recorded yet")

# Serial number analysis
print("\n" + "=" * 70)
print("SERIAL NUMBER ANALYSIS")
print("=" * 70)

print("\n🔢 Serial Number Patterns:")
print("-" * 70)
for item in all_items:
    serial = item.serial
    has_paf = 'PAF' in serial.upper()
    length = len(serial)
    has_spaces = ' ' in serial
    
    notes = []
    if has_paf:
        notes.append("Contains PAF")
    if has_spaces:
        notes.append("Has spaces")
    if length < 5:
        notes.append("Short serial")
    elif length > 20:
        notes.append("Long serial")
    
    note_str = ", ".join(notes) if notes else "Standard"
    print(f"  {item.item_type:8} | {serial:30} | Length: {length:2} | {note_str}")

# Check for QR codes
print("\n" + "=" * 70)
print("QR CODE STATUS")
print("=" * 70)

items_with_qr = Item.objects.exclude(Q(qr_code='') | Q(qr_code__isnull=True)).count()
items_without_qr = Item.objects.filter(Q(qr_code='') | Q(qr_code__isnull=True)).count()

print(f"\n  Items with QR Code: {items_with_qr}")
print(f"  Items without QR Code: {items_without_qr}")

if items_without_qr > 0:
    print("\n  Items needing QR codes:")
    for item in Item.objects.filter(Q(qr_code='') | Q(qr_code__isnull=True)):
        print(f"    {item.item_type:8} {item.serial}")

print("\n" + "=" * 70)
print("Analysis Complete")
print("=" * 70)
