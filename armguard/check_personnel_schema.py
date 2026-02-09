import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from personnel.models import Personnel

print("Personnel count:", Personnel.all_objects.count())
print("\nFields:")
for f in Personnel._meta.fields:
    print(f" - {f.name}: {f.get_internal_type()}")

if Personnel.all_objects.exists():
    print("\nFirst personnel record:")
    p = Personnel.all_objects.first()
    print(f"  ID: {p.id}")
    print(f"  Name: {p.get_full_name()}")
    print(f"  created_at: {p.created_at}")
    print(f"  updated_at: {p.updated_at}")
    print(f"  created_by: {p.created_by}")
    print(f"  modified_by: {p.modified_by}")
