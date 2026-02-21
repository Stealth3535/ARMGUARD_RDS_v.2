from inventory.models import Item
from django.db.models import Max

item_types = Item.objects.values_list('item_type', flat=True).distinct()
total = 0
for itype in item_types:
    items = Item.objects.filter(item_type=itype, item_number__isnull=True).order_by('created_at', 'serial')
    max_num = Item.objects.filter(item_type=itype, item_number__isnull=False).aggregate(Max('item_number'))['item_number__max'] or 0
    for i, item in enumerate(items, start=max_num+1):
        Item.objects.filter(pk=item.pk).update(item_number=i)
        total += 1
    print(f'{itype}: assigned {items.count()} numbers starting from {max_num+1}')
print(f'Total updated: {total}')
