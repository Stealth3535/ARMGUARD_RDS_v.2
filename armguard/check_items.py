"""
Check current M4 status
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from inventory.models import Item

print("Current items in database:")
for item in Item.objects.all().order_by('id'):
    print(f"  ID: {item.id}")
    print(f"  Type: {item.item_type}")
    print(f"  Serial: {item.serial}")
    print(f"  QR Code: {item.qr_code}")
    print("-" * 50)
