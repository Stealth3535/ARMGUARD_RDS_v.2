import os
import django
from django.db.models import Q

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User
from personnel.models import Personnel

print('=== TESTING USER MANAGEMENT QUERY ===\n')

# Exact query from user_management view
admin_users = User.objects.select_related('userprofile').prefetch_related('groups').filter(
    Q(is_superuser=True) | Q(groups__name__in=['Admin', 'Armorer'])
).distinct().order_by('-date_joined')

print(f'Admin users count: {admin_users.count()}')
for user in admin_users:
    try:
        personnel = Personnel.objects.get(user=user)
        personnel_info = f' -> Personnel: {personnel.get_full_name()}'
    except Personnel.DoesNotExist:
        personnel_info = ' -> No personnel'
    
    print(f'  {user.username} (Super: {user.is_superuser}, Staff: {user.is_staff}){personnel_info}')

print('\n=== CHECKING RDS USER SPECIFICALLY ===')
rds = User.objects.get(username='rds')
print(f'Username: {rds.username}')
print(f'is_superuser: {rds.is_superuser}')
print(f'is_staff: {rds.is_staff}')
print(f'is_active: {rds.is_active}')
print(f'Groups: {[g.name for g in rds.groups.all()]}')
print(f'Match Q(is_superuser=True): {rds.is_superuser == True}')

# Check if in queryset
if rds in admin_users:
    print(f'✓ RDS user IS in admin_users queryset')
else:
    print(f'✗ RDS user is NOT in admin_users queryset')
