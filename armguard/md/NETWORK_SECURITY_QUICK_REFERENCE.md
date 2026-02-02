# ArmGuard Network Security Quick Reference

## Network Access Control Implementation

### Quick Start Checklist

✅ **Middleware Added**: Network security middleware in settings.py  
✅ **Decorators Applied**: @lan_required and @read_only_on_wan on views  
✅ **Settings Configured**: Network ports and path restrictions  
✅ **Context Added**: Network context processor for templates  

## Decorator Usage

### @lan_required
**Use for**: Sensitive operations (create, edit, delete)
```python
from core.network_decorators import lan_required

@login_required
@lan_required
def sensitive_operation(request):
    """This function requires LAN access"""
    pass
```

### @read_only_on_wan
**Use for**: Status checking and reporting
```python
from core.network_decorators import read_only_on_wan

@login_required
@read_only_on_wan
def view_status(request):
    """This function allows WAN read-only access"""
    pass
```

## Template Context

### Check Network Type
```html
{% if is_lan_access %}
    <!-- Show create/edit buttons -->
    <a href="{% url 'create' %}" class="btn btn-primary">Create</a>
{% else %}
    <!-- Show read-only message -->
    <div class="alert alert-info">LAN access required for modifications</div>
{% endif %}

{% if is_wan_access %}
    <span class="badge badge-secondary">Read-Only Mode</span>
{% endif %}
```

## Network Configuration

### Port Assignment
- **Port 8443**: LAN access (full functionality)
- **Port 443**: WAN access (read-only operations)

### Path Categories

#### LAN-Only Paths
- `/admin/` - Administrative functions
- `/transactions/qr-scanner/` - QR scanning
- `/transactions/create/` - Transaction creation
- `/inventory/add/` - Inventory management
- `/users/register/` - User registration

#### WAN Read-Only Paths
- `/personnel/` - Personnel information
- `/inventory/` - Inventory viewing
- `/transactions/history/` - Transaction history
- `/reports/` - Status reports

## Security By App

| App | LAN Operations | WAN Operations |
|-----|---------------|----------------|
| **Transactions** | Create, Edit, Delete | History, Status |
| **Users** | Registration | Login, Profile |
| **Personnel** | Registration | View, Search |
| **Inventory** | Add, Edit, Delete | View, Reports |
| **Admin** | All Functions | ❌ Blocked |

## Applied Security Decorators

### Transactions Views
```python
@lan_required - qr_transaction_scanner()
@lan_required - create_qr_transaction()
```

### Users Views
```python
@lan_required - UserRegistrationView.dispatch()
```

### Personnel Views
```python
@read_only_on_wan - personnel_profile_list()
@read_only_on_wan - personnel_profile_detail()
```

### Inventory Views
```python
@read_only_on_wan - ItemListView.dispatch()
@read_only_on_wan - ItemDetailView.dispatch()
```

### Admin Views
```python
@lan_required - universal_registration()
```

## Testing Network Security

### Test LAN Access (Port 8443)
```bash
# Should work - sensitive operations
curl -k https://armguard.local:8443/admin/
curl -k https://armguard.local:8443/transactions/create/

# Should work - all operations
curl -k https://armguard.local:8443/personnel/
```

### Test WAN Access (Port 443)
```bash
# Should be blocked - sensitive operations
curl -k https://armguard.example.com:443/admin/
curl -k https://armguard.example.com:443/transactions/create/

# Should work - read-only operations
curl -k https://armguard.example.com:443/personnel/
curl -k https://armguard.example.com:443/transactions/history/
```

## Security Enforcement

### Automatic Enforcement
- **Middleware**: Detects network type and enforces restrictions
- **Decorators**: Apply view-level security controls
- **Settings**: Configure path and role restrictions
- **Context**: Provide template-level network awareness

### Manual Checks
```python
# In views
if request.META.get('SERVER_PORT') == '8443':
    # LAN access
    pass
else:
    # WAN access - restrict operations
    pass

# In templates
{% if is_lan_access %}
    <!-- LAN functionality -->
{% elif is_wan_access %}
    <!-- WAN read-only functionality -->
{% endif %}
```

## Role-Based Network Access

### Admin Users
- **LAN**: Full access required for security
- **WAN**: ❌ Blocked for administrative safety

### Staff Users
- **LAN**: Full operational access
- **WAN**: Read-only status checking

### Regular Users
- **LAN**: ❌ No direct access needed
- **WAN**: Status checking only

## Session Security

### Session Timeouts
- **LAN**: 120 minutes (secure environment)
- **WAN**: 30 minutes (external access)

### Session Invalidation
- Automatic logout on network type change
- Enhanced security for cross-network access

## Common Patterns

### View Function Pattern
```python
@login_required
@lan_required  # or @read_only_on_wan
def my_view(request):
    """
    Network security is automatically enforced
    """
    # Your view logic here
    pass
```

### Class-Based View Pattern
```python
class MyView(LoginRequiredMixin, View):
    @lan_required  # or @read_only_on_wan
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)
```

### Template Pattern
```html
{% load network_tags %}

<div class="card">
    <div class="card-header">
        Operations
        {% if is_wan_access %}
            <span class="badge badge-info">Read-Only</span>
        {% endif %}
    </div>
    <div class="card-body">
        {% if is_lan_access %}
            <button class="btn btn-primary">Create</button>
            <button class="btn btn-warning">Edit</button>
            <button class="btn btn-danger">Delete</button>
        {% else %}
            <p class="text-muted">
                Modification operations require LAN access
            </p>
        {% endif %}
    </div>
</div>
```

## Troubleshooting

### Network Not Detected
1. Check middleware order in settings.py
2. Verify server port configuration
3. Check network_middleware.py imports

### Operations Blocked Unexpectedly
1. Verify decorator application
2. Check path configuration in settings
3. Review security logs

### Templates Not Showing Network Status
1. Verify context processor in settings
2. Check template {% if is_lan_access %} syntax
3. Ensure proper template inheritance

## Security Validation

### Pre-Deployment Checklist
- [ ] All sensitive views have @lan_required
- [ ] All status views have @read_only_on_wan
- [ ] Middleware is properly configured
- [ ] Network settings are correct
- [ ] Templates show appropriate controls
- [ ] Security tests pass

### Post-Deployment Verification
- [ ] LAN operations work on port 8443
- [ ] WAN operations blocked on sensitive paths
- [ ] WAN read-only operations work on port 443
- [ ] Security logging is active
- [ ] Session timeouts are enforced

---

**Quick Reference Version**: 1.0  
**Implementation Status**: ✅ Complete  
**Security Level**: Military Grade