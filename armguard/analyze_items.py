"""
Analyze Items Database
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from inventory.models import Item
from django.db.models import Count, Q
from transactions.models import Transaction

print("=" * 60)
print("ITEM DATABASE ANALYSIS")
print("=" * 60)

# Total items
total = Item.objects.count()
print(f"\n📊 Total Items: {total}")

# Item types breakdown
print("\n🔫 ITEM TYPES:")
print("-" * 40)
item_types = Item.objects.values('item_type').annotate(count=Count('item_type')).order_by('-count')
for item in item_types:
    percentage = (item['count'] / total * 100) if total > 0 else 0
    print(f"  {item['item_type']:15} {item['count']:4} ({percentage:5.1f}%)")

# Status breakdown
print("\n📋 ITEM STATUS:")
print("-" * 40)
statuses = Item.objects.values('status').annotate(count=Count('status')).order_by('-count')
for item in statuses:
    percentage = (item['count'] / total * 100) if total > 0 else 0
    print(f"  {item['status']:15} {item['count']:4} ({percentage:5.1f}%)")

# Condition breakdown
print("\n🔧 ITEM CONDITION:")
print("-" * 40)
conditions = Item.objects.values('condition').annotate(count=Count('condition')).order_by('-count')
for item in conditions:
    percentage = (item['count'] / total * 100) if total > 0 else 0
    print(f"  {item['condition']:15} {item['count']:4} ({percentage:5.1f}%)")

# Rifles vs Pistols
print("\n🎯 CATEGORY BREAKDOWN:")
print("-" * 40)
rifles = Item.objects.filter(item_type__in=['M14', 'M16', 'M4']).count()
pistols = Item.objects.filter(item_type__in=['GLOCK', '45']).count()
print(f"  Rifles:         {rifles:4} ({rifles/total*100 if total > 0 else 0:5.1f}%)")
print(f"  Pistols:        {pistols:4} ({pistols/total*100 if total > 0 else 0:5.1f}%)")

# Sample of recent items
print("\n📦 SAMPLE OF ITEMS (Last 10):")
print("-" * 40)
recent_items = Item.objects.order_by('-created_at')[:10]
for item in recent_items:
    print(f"  {item.id:20} {item.item_type:8} {item.serial:20} {item.status:12} {item.condition}")

# Items with issues
print("\n⚠️  ITEMS REQUIRING ATTENTION:")
print("-" * 40)
maintenance = Item.objects.filter(status='Maintenance').count()
poor_condition = Item.objects.filter(condition__in=['Poor', 'Damaged']).count()
retired = Item.objects.filter(status='Retired').count()
print(f"  In Maintenance:  {maintenance}")
print(f"  Poor/Damaged:    {poor_condition}")
print(f"  Retired:         {retired}")

# Currently issued items
print("\n📤 ISSUED ITEMS:")
print("-" * 40)
issued = Item.objects.filter(status='Issued').count()
print(f"  Currently Issued: {issued}")
if issued > 0:
    print("\n  Last 5 Issued Items:")
    issued_items = Item.objects.filter(status='Issued').order_by('-updated_at')[:5]
    for item in issued_items:
        # Try to get the last transaction
        last_trans = Transaction.objects.filter(item=item, action='Take').order_by('-date_time').first()
        if last_trans:
            print(f"    {item.item_type:8} {item.serial:20} → {last_trans.personnel.get_full_name()}")
        else:
            print(f"    {item.item_type:8} {item.serial:20} → Unknown")

# Duplicate serials check
print("\n🔍 DATA INTEGRITY:")
print("-" * 40)
from django.db.models import Count
duplicates = Item.objects.values('serial').annotate(count=Count('serial')).filter(count__gt=1)
if duplicates.count() > 0:
    print(f"  ⚠️  Duplicate Serials Found: {duplicates.count()}")
    for dup in duplicates:
        print(f"     Serial '{dup['serial']}' appears {dup['count']} times")
else:
    print("  ✓ No duplicate serials found")

# Items without serials or descriptions
no_serial = Item.objects.filter(Q(serial='') | Q(serial__isnull=True)).count()
no_desc = Item.objects.filter(Q(description='') | Q(description__isnull=True)).count()
print(f"  Items without serial: {no_serial}")
print(f"  Items without description: {no_desc}")

print("\n" + "=" * 60)
print("Analysis Complete")
print("=" * 60)
