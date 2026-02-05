# Admin Interface Documentation

## Overview
The ArmGuard system now has a custom admin interface that allows you to create admin users who have elevated privileges but do not have access to the Django admin site. This provides better security and separation of concerns.

## User Types

### 1. Regular User
- `is_staff = False`
- `is_superuser = False`
- Can access the main application features
- Cannot access admin panel or Django admin

### 2. Admin User (Staff)
- `is_staff = True`
- `is_superuser = False`
- Can access custom admin panel at `/admin/`
- Can manage regular users
- **Cannot** access Django admin site
- **Cannot** create or manage other admin/superusers (unless granted by superuser)

### 3. Superuser
- `is_staff = True`
- `is_superuser = True`
- Full system access
- Can access custom admin panel at `/admin/`
- Can access Django admin site at `/superadmin/`
- Can create, edit, and delete all user types

## Creating Users

### Create Admin User (Command Line)
```powershell
python manage.py createadmin <username> --password <password>
```

Example:
```powershell
python manage.py createadmin adminuser --password admin123
```

### Create Superuser (Command Line)
```powershell
python manage.py createsuperuser
```

### Create Users via Custom Admin Interface
1. Log in as an admin or superuser
2. Navigate to `/admin/`
3. Click "Manage Users"
4. Click "Create New User"
5. Fill in the form:
   - Username (required)
   - Password (required)
   - First Name, Last Name, Email (optional)
   - Check "Admin User" to make them staff
   - Check "Superuser" to give them full access (superusers only)

## Custom Admin Features

### Admin Dashboard (`/admin/`)
- View system statistics:
  - Total Items
  - Total Personnel
  - Total Transactions
  - Total Users
- Quick action buttons to navigate to:
  - User Management
  - Personnel List
  - Inventory List
  - Transactions
  - Django Admin (superusers only)
- Recent transactions list

### User Management (`/admin/users/`)
- View all users in the system
- See user roles (Superuser/Admin/User)
- See user status (Active/Inactive)
- Edit user details
- Delete users (with restrictions)

### User Creation (`/admin/users/create/`)
- Create new users
- Set staff status
- Set superuser status (superusers only)

### User Editing (`/admin/users/<id>/edit/`)
- Edit user information
- Change passwords
- Toggle active status
- Modify roles (superusers only)

### System Settings (`/admin/settings/`)
- View system information
- Check debug status
- Access Django admin (superusers only)

## Access Control

### Who Can Access What?

| Feature | Regular User | Admin User | Superuser |
|---------|-------------|------------|-----------|
| Main App | ✅ | ✅ | ✅ |
| Custom Admin Panel | ❌ | ✅ | ✅ |
| Create Regular Users | ❌ | ✅ | ✅ |
| Create Admin Users | ❌ | ❌ | ✅ |
| Create Superusers | ❌ | ❌ | ✅ |
| Edit Own Profile | ✅ | ✅ | ✅ |
| Edit Other Users | ❌ | ✅* | ✅ |
| Delete Users | ❌ | ✅* | ✅ |
| Django Admin (`/superadmin/`) | ❌ | ❌ | ✅ |

*Admin users can only edit/delete regular users, not other admins or superusers

## URL Structure

```
/login/                          - Login page
/logout/                         - Logout
/                                - Main dashboard
/admin/                          - Custom admin dashboard (staff only)
/admin/users/                    - User management (staff only)
/admin/users/create/             - Create user (staff only)
/admin/users/<id>/edit/          - Edit user (staff only)
/admin/users/<id>/delete/        - Delete user (staff only)
/admin/settings/                 - System settings (staff only)
/superadmin/                     - Django admin (superusers only)
```

## Security Features

1. **Role-Based Access Control**: Different user types have different permissions
2. **Self-Protection**: Users cannot delete their own accounts
3. **Hierarchy Protection**: Admin users cannot modify superusers
4. **Django Admin Restriction**: Only superusers can access `/superadmin/`
5. **Custom Admin Access**: All staff users can access custom admin panel
6. **Password Protection**: Passwords are hashed and secure

## Testing the Admin Interface

### Test as Admin User:
1. Create admin user: `python manage.py createadmin testadmin --password admin123`
2. Login at http://127.0.0.1:8000/login/
3. Username: `testadmin`, Password: `admin123`
4. Navigate to "Admin" in the navbar
5. You should see:
   - Admin dashboard with statistics
   - User management option
   - Quick action buttons
6. Try accessing `/superadmin/` - you should be redirected/denied

### Test as Superuser:
1. Create superuser: `python manage.py createsuperuser`
2. Login at http://127.0.0.1:8000/login/
3. Navigate to "Admin" in the navbar
4. You should see:
   - All admin features
   - "Django Admin" button (red)
   - Ability to create superusers
5. Access `/superadmin/` - you should see Django's admin interface

## Default Credentials

### Superuser (if created):
- Username: `admin`
- Password: `admin123`

### Admin User (if created):
- Username: `adminuser`
- Password: `admin123`

**IMPORTANT**: Change these default passwords in production!

## Troubleshooting

### "Permission Denied" when accessing `/admin/`
- Make sure the user has `is_staff = True`
- Check if user is logged in
- Verify user has active status

### Cannot create superusers in custom admin
- Only superusers can create other superusers
- Login as a superuser first

### Django admin shows login error
- Django admin at `/superadmin/` is for superusers only
- Use custom admin at `/admin/` for staff users

## Customization

To customize the admin interface:

1. **Templates**: Edit files in `admin/templates/admin/`
   - `dashboard.html` - Main admin page
   - `user_management.html` - User list
   - `create_user.html` - User creation form
   - `edit_user.html` - User edit form
   - `system_settings.html` - Settings page

2. **Views**: Edit `admin/views.py` to modify functionality

3. **URLs**: Edit `admin/urls.py` to add new admin pages

4. **Styling**: Inline CSS in templates or add to `core/static/css/main.css`

## Best Practices

1. **Use Custom Admin**: Regular staff should use `/admin/`, not `/superadmin/`
2. **Limit Superusers**: Only create superusers when necessary
3. **Strong Passwords**: Use strong passwords for all admin accounts
4. **Regular Audits**: Review user list regularly
5. **Deactivate, Don't Delete**: Consider deactivating users instead of deleting
6. **Role Separation**: Use admin users for day-to-day management, superusers for system tasks

## Future Enhancements

Possible improvements:
- Activity logging for admin actions
- Password reset functionality
- Bulk user operations
- User permissions system
- Email notifications
- Two-factor authentication
- API access controls
