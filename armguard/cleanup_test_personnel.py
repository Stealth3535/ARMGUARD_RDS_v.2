import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from personnel.models import Personnel

# Delete any test personnel records
test_serials = ['888888']
for serial in test_serials:
    test_records = Personnel.all_objects.filter(serial=serial)
    if test_records.exists():
        for record in test_records:
            print(f"Deleting test personnel: {record.id} - {record.get_full_name()}")
            record.delete()  # Hard delete
print("Test data cleanup complete!")
