# UNIVERSALFORM QUICK REFERENCE

## Usage in Views

```python
from admin.forms import UniversalForm

# CREATE USER + PERSONNEL
def register_new_user(request):
    if request.method == 'POST':
        form = UniversalForm(request.POST, request.FILES)
        # operation_type will be 'create_user_with_personnel' from form
        if form.is_valid():
            user, personnel = form.save()
            # user = User object
            # personnel = Personnel object
            return redirect('success_page')
    else:
        form = UniversalForm(initial={'operation_type': 'create_user_with_personnel'})
    return render(request, 'register.html', {'form': form})

# EDIT USER
def edit_user_view(request, user_id):
    user_obj = User.objects.get(id=user_id)
    if request.method == 'POST':
        form = UniversalForm(request.POST, request.FILES, edit_user=user_obj)
        if form.is_valid():
            user, _ = form.save()
            return redirect('success_page')
    else:
        form = UniversalForm(
            edit_user=user_obj,
            initial={'operation_type': 'edit_user'}
        )
    return render(request, 'edit_user.html', {'form': form})

# EDIT PERSONNEL
def edit_personnel_view(request, personnel_id):
    personnel_obj = Personnel.objects.get(id=personnel_id)
    if request.method == 'POST':
        form = UniversalForm(request.POST, request.FILES, edit_personnel=personnel_obj)
        if form.is_valid():
            _, personnel = form.save()
            return redirect('success_page')
    else:
        form = UniversalForm(
            edit_personnel=personnel_obj,
            initial={'operation_type': 'edit_personnel'}
        )
    return render(request, 'edit_personnel.html', {'form': form})

# EDIT BOTH USER + PERSONNEL
def edit_both_view(request, user_id):
    user_obj = User.objects.get(id=user_id)
    personnel_obj = user_obj.personnel
    if request.method == 'POST':
        form = UniversalForm(
            request.POST, 
            request.FILES,
            edit_user=user_obj,
            edit_personnel=personnel_obj
        )
        if form.is_valid():
            user, personnel = form.save()
            return redirect('success_page')
    else:
        form = UniversalForm(
            edit_user=user_obj,
            edit_personnel=personnel_obj,
            initial={'operation_type': 'edit_both'}
        )
    return render(request, 'edit_both.html', {'form': form})
```

---

## Operation Types

| operation_type | Description | User | Personnel |
|---------------|-------------|------|-----------|
| `create_user_only` | Create user account only | ✓ | ✗ |
| `create_personnel_only` | Create personnel record only | ✗ | ✓ |
| `create_user_with_personnel` | Full registration | ✓ | ✓ |
| `edit_user` | Edit user account | ✓ | ✗ |
| `edit_personnel` | Edit personnel record | ✗ | ✓ |
| `edit_both` | Edit user + personnel | ✓ | ✓ |

---

## Required Fields by Operation

### create_user_only / edit_user
- username
- first_name
- last_name
- password (create only)
- confirm_password (create only)

### create_personnel_only / edit_personnel
- surname
- firstname
- rank
- serial
- personnel_group
- tel

### create_user_with_personnel / edit_both
- All user fields +
- All personnel fields

---

## Role Choices

| Role | Django Group | is_staff | is_superuser | is_armorer |
|------|-------------|----------|-------------|------------|
| `regular` | - | False | False | False |
| `armorer` | Armorer | True | False | True |
| `admin` | Admin | True | False | False |
| `superuser` | - | True | True | False |

---

## Phone Number Conversion

Input formats accepted:
- `09XXXXXXXXX` (11 digits) → Converted to `+639XXXXXXXXX`
- `+639XXXXXXXXX` (13 digits) → Stored as-is

Both `phone_number` (UserProfile) and `tel` (Personnel) fields support this.

---

## Classification Auto-Detection

| Rank Type | Classification |
|-----------|---------------|
| Enlisted (AM, SGT, TSGT, etc.) | ENLISTED PERSONNEL |
| Officer (2LT, 1LT, CPT, etc.) | OFFICER |
| No rank + is_superuser | SUPERUSER |

---

## Group Choices

Available groups:
- `HAS`
- `951st`
- `952nd`
- `953rd`

Note: `group` (UserProfile) and `personnel_group` (Personnel) are separate fields.

---

## Return Values

```python
user, personnel = form.save()
```

Returns:
- `user`: User object (or None if personnel-only operation)
- `personnel`: Personnel object (or None if user-only operation)

---

## Form Validation Errors

Access errors:
```python
if not form.is_valid():
    print(form.errors)  # Dictionary of field errors
    print(form.non_field_errors())  # List of non-field errors
```

Common validation errors:
- Duplicate username
- Duplicate serial number
- Password mismatch
- Invalid phone format
- Missing required fields

---

## Pre-population for Editing

```python
# Pre-populate form with existing user data
form = UniversalForm(edit_user=user_obj)

# Pre-populate form with existing personnel data
form = UniversalForm(edit_personnel=personnel_obj)

# Pre-populate both
form = UniversalForm(edit_user=user_obj, edit_personnel=personnel_obj)
```

The form's `__init__` method automatically populates fields from the provided objects.

---

## Template Example

```html
<form method="post" enctype="multipart/form-data">
    {% csrf_token %}
    
    <!-- Operation type selector -->
    {{ form.operation_type.label_tag }}
    {{ form.operation_type }}
    
    <!-- User fields -->
    <h3>User Account</h3>
    {{ form.username.label_tag }} {{ form.username }}
    {{ form.first_name.label_tag }} {{ form.first_name }}
    {{ form.last_name.label_tag }} {{ form.last_name }}
    {{ form.email.label_tag }} {{ form.email }}
    {{ form.password.label_tag }} {{ form.password }}
    {{ form.confirm_password.label_tag }} {{ form.confirm_password }}
    {{ form.role.label_tag }} {{ form.role }}
    {{ form.group.label_tag }} {{ form.group }}
    {{ form.phone_number.label_tag }} {{ form.phone_number }}
    
    <!-- Personnel fields -->
    <h3>Personnel Information</h3>
    {{ form.surname.label_tag }} {{ form.surname }}
    {{ form.firstname.label_tag }} {{ form.firstname }}
    {{ form.middle_initial.label_tag }} {{ form.middle_initial }}
    {{ form.rank.label_tag }} {{ form.rank }}
    {{ form.serial.label_tag }} {{ form.serial }}
    {{ form.personnel_group.label_tag }} {{ form.personnel_group }}
    {{ form.tel.label_tag }} {{ form.tel }}
    {{ form.personnel_status.label_tag }} {{ form.personnel_status }}
    
    <!-- Pictures -->
    {{ form.profile_picture.label_tag }} {{ form.profile_picture }}
    {{ form.personnel_picture.label_tag }} {{ form.personnel_picture }}
    
    <button type="submit">Save</button>
</form>
```

---

## JavaScript (Optional)

Show/hide fields based on operation_type:

```javascript
document.getElementById('operationType').addEventListener('change', function() {
    const type = this.value;
    const userFields = document.querySelectorAll('.user-field');
    const personnelFields = document.querySelectorAll('.personnel-field');
    
    if (type.includes('user')) {
        userFields.forEach(f => f.style.display = 'block');
    } else {
        userFields.forEach(f => f.style.display = 'none');
    }
    
    if (type.includes('personnel')) {
        personnelFields.forEach(f => f.style.display = 'block');
    } else {
        personnelFields.forEach(f => f.style.display = 'none');
    }
});
```

---

## Testing

Run comprehensive tests:
```bash
python test_comprehensive_system.py
```

Run basic form test:
```bash
python test_universal_form.py
```

---

**END OF QUICK REFERENCE**
