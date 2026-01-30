"""
Admin Forms - Single Comprehensive Form System

MAIN FORM:
- UniversalForm - Handles all user and personnel operations (create, edit, combined)

UTILITY FORMS:
- ItemRegistrationForm - Inventory management
- SystemSettingsForm - System configuration  
- PersonnelRegistrationForm - Legacy support (kept for compatibility)
"""
from django import forms
from django.contrib.auth.models import User, Group
from django.core.exceptions import ValidationError
from personnel.models import Personnel
from inventory.models import Item
from users.models import UserProfile


class UniversalForm(forms.Form):
    """
    SINGLE COMPREHENSIVE FORM FOR ALL OPERATIONS
    Handles: User Registration, Personnel Registration, User Editing, Personnel Editing, Combined Operations
    """
    
    # === OPERATION TYPE ===
    OPERATION_TYPES = [
        ('create_user_only', 'Create User Account Only'),
        ('create_personnel_only', 'Create Personnel Record Only'),
        ('create_user_with_personnel', 'Create User Account + Personnel Record'),
    ]
    
    # All operation types including edit (used internally)
    ALL_OPERATION_TYPES = OPERATION_TYPES + [
        ('edit_user', 'Edit User Account'),
        ('edit_personnel', 'Edit Personnel Record'),
        ('edit_both', 'Edit User + Personnel'),
    ]
    
    operation_type = forms.ChoiceField(
        choices=ALL_OPERATION_TYPES,
        initial='create_user_with_personnel',
        widget=forms.HiddenInput(attrs={'id': 'operationType'}),
        help_text='Automatically determined by role selection',
        required=False
    )
    
    # Hidden fields for editing
    edit_user_id = forms.IntegerField(required=False, widget=forms.HiddenInput())
    edit_personnel_id = forms.CharField(required=False, widget=forms.HiddenInput())  # CharField because Personnel.id is PE/PO format
    
    # === USER ACCOUNT FIELDS ===
    username = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    first_name = forms.CharField(max_length=30, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=30, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(required=False, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    password = forms.CharField(required=False, widget=forms.PasswordInput(attrs={'class': 'form-control'}), help_text="Leave blank to keep existing password (when editing)")
    confirm_password = forms.CharField(required=False, widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    is_active = forms.BooleanField(required=False, initial=True, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    
    # === USER ROLE ===
    ROLE_CHOICES = [('personnel', 'Personnel'), ('armorer', 'Armorer'), ('admin', 'Administrator')]
    role = forms.ChoiceField(choices=ROLE_CHOICES, initial='personnel', required=False, widget=forms.Select(attrs={'class': 'form-control'}))
    
    # === USER PROFILE FIELDS ===
    GROUP_CHOICES = [('', 'Select Group'), ('HAS', 'HAS'), ('951st', '951st'), ('952nd', '952nd'), ('953rd', '953rd')]
    group = forms.ChoiceField(choices=GROUP_CHOICES, required=False, widget=forms.Select(attrs={'class': 'form-control'}))
    phone_number = forms.CharField(max_length=15, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    department = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}), help_text="Department assignment (optional)")
    profile_picture = forms.ImageField(required=False, widget=forms.FileInput(attrs={'class': 'form-control-file'}))
    
    # === PERSONNEL FIELDS ===
    surname = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    firstname = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    middle_initial = forms.CharField(max_length=1, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'maxlength': '1'}))
    rank = forms.ChoiceField(choices=Personnel.ALL_RANKS, required=False, widget=forms.Select(attrs={'class': 'form-control'}))
    serial = forms.CharField(max_length=20, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}), help_text="Serial number (6 digits for enlisted, or O-XXXXXX for officers)")
    personnel_group = forms.ChoiceField(choices=Personnel.GROUP_CHOICES, required=False, widget=forms.Select(attrs={'class': 'form-control'}))
    tel = forms.CharField(max_length=13, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'maxlength': '13'}), help_text="Phone number (will auto-convert 09XXXXXXXXX to +639XXXXXXXXX)")
    personnel_status = forms.ChoiceField(choices=Personnel.STATUS_CHOICES, required=False, widget=forms.Select(attrs={'class': 'form-control'}), initial='Active')
    personnel_picture = forms.ImageField(required=False, widget=forms.FileInput(attrs={'class': 'form-control-file'}))
    
    def __init__(self, *args, **kwargs):
        self.edit_user = kwargs.pop('edit_user', None)
        self.edit_personnel = kwargs.pop('edit_personnel', None)
        super().__init__(*args, **kwargs)
        
        if self.edit_user:
            self.initial.update({
                'edit_user_id': self.edit_user.id,
                'username': self.edit_user.username,
                'first_name': self.edit_user.first_name,
                'last_name': self.edit_user.last_name,
                'email': self.edit_user.email,
                'is_active': self.edit_user.is_active,
                'role': 'superuser' if self.edit_user.is_superuser else 'admin' if self.edit_user.groups.filter(name='Admin').exists() else 'armorer' if self.edit_user.groups.filter(name='Armorer').exists() else 'personnel'
            })
            try:
                profile = self.edit_user.userprofile
                self.initial.update({'group': profile.group or '', 'phone_number': profile.phone_number or ''})
            except AttributeError:
                # User doesn't have a profile yet
                pass
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning("Error accessing user profile: %s", str(e))
        
        if self.edit_personnel:
            self.initial.update({
                'edit_personnel_id': self.edit_personnel.id,
                'surname': self.edit_personnel.surname,
                'firstname': self.edit_personnel.firstname,
                'middle_initial': self.edit_personnel.middle_initial,
                'rank': self.edit_personnel.rank,
                'serial': self.edit_personnel.serial,
                'personnel_group': self.edit_personnel.group,
                'tel': self.edit_personnel.tel,
                'personnel_status': self.edit_personnel.status
            })
    
    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get('role')
        operation_type = cleaned_data.get('operation_type')
        
        # Auto-set operation_type based on role if not in edit mode
        if not self.edit_user and not self.edit_personnel:
            if role == 'personnel':
                cleaned_data['operation_type'] = 'create_personnel_only'
                operation_type = 'create_personnel_only'
            elif role in ['armorer', 'admin']:
                cleaned_data['operation_type'] = 'create_user_with_personnel'
                operation_type = 'create_user_with_personnel'
        
        # Dynamic validation based on operation type
        if operation_type in ['create_user_only', 'edit_user']:
            # Only require user fields when creating/editing user without personnel
            for field in ['username', 'first_name', 'last_name']:
                if not cleaned_data.get(field):
                    self.add_error(field, f'This field is required for {operation_type} operation.')
        elif operation_type in ['create_user_with_personnel', 'edit_both']:
            # For user with personnel, only username is required (names come from personnel)
            if not cleaned_data.get('username'):
                self.add_error('username', f'This field is required for {operation_type} operation.')
            
        if operation_type in ['create_user_only', 'create_user_with_personnel', 'edit_user', 'edit_both']:
            if operation_type.startswith('create_'):
                password = cleaned_data.get('password')
                if not password:
                    self.add_error('password', 'Password is required for new user creation.')
                elif password != cleaned_data.get('confirm_password'):
                    self.add_error('confirm_password', 'Passwords do not match.')
        
        if operation_type in ['create_personnel_only', 'create_user_with_personnel', 'edit_personnel', 'edit_both']:
            for field in ['surname', 'firstname', 'rank', 'serial', 'personnel_group', 'tel']:
                if not cleaned_data.get(field):
                    self.add_error(field, f'This field is required for {operation_type} operation.')
        
        # Tel validation and conversion
        tel = cleaned_data.get('tel')
        if tel:
            if tel.startswith('09') and len(tel) == 11 and tel.isdigit():
                cleaned_data['tel'] = '+63' + tel[1:]
            elif not tel.startswith('+639') or len(tel) != 13:
                self.add_error('tel', 'Phone number must be in +639XXXXXXXXX format or 09XXXXXXXXX format.')
        
        # Check serial uniqueness (check ALL records including soft-deleted)
        serial = cleaned_data.get('serial')
        if serial:
            if operation_type in ['create_personnel_only', 'create_user_with_personnel']:
                # For new personnel, check if serial exists (including deleted records)
                existing = Personnel.all_objects.filter(serial=serial).first()
                if existing:
                    if existing.deleted_at:
                        # Allow re-registration - will reactivate in save()
                        cleaned_data['_reactivate_personnel'] = existing
                    else:
                        self.add_error('serial', 'This serial number is already registered.')
            elif operation_type in ['edit_personnel', 'edit_both']:
                # For editing personnel, check if serial exists for OTHER personnel
                edit_personnel_id = cleaned_data.get('edit_personnel_id')
                if edit_personnel_id:
                    existing = Personnel.all_objects.filter(serial=serial).exclude(id=edit_personnel_id).first()
                    if existing:
                        if existing.deleted_at:
                            self.add_error('serial', f'This serial number was previously registered to {existing.get_full_name()} (deleted). Please use a different serial number.')
                        else:
                            self.add_error('serial', 'This serial number is already registered to another personnel.')
        
        # Check username uniqueness
        username = cleaned_data.get('username')
        if username:
            if operation_type in ['create_user_only', 'create_user_with_personnel']:
                # For new users, check if username exists
                if User.objects.filter(username=username).exists():
                    self.add_error('username', 'This username is already taken.')
            elif operation_type in ['edit_user', 'edit_both']:
                # For editing users, check if username exists for OTHER users
                edit_user_id = cleaned_data.get('edit_user_id')
                if edit_user_id:
                    if User.objects.filter(username=username).exclude(id=edit_user_id).exists():
                        self.add_error('username', 'This username is already taken by another user.')
        
        return cleaned_data
    
    def save(self, commit=True):
        operation_type = self.cleaned_data['operation_type']
        user = None
        personnel = None
        
        if operation_type in ['create_user_only', 'create_user_with_personnel']:
            # For armorer/admin, use personnel names if not provided
            first_name = self.cleaned_data.get('first_name')
            last_name = self.cleaned_data.get('last_name')
            
            if operation_type == 'create_user_with_personnel':
                # Use personnel data if user fields not provided
                if not first_name:
                    first_name = self.cleaned_data.get('firstname', '')
                if not last_name:
                    last_name = self.cleaned_data.get('surname', '')
            
            user = User.objects.create_user(
                username=self.cleaned_data['username'],
                password=self.cleaned_data['password'],
                email=self.cleaned_data.get('email', ''),
                first_name=first_name or '',
                last_name=last_name or '',
                is_active=self.cleaned_data.get('is_active', True)
            )
            
            role = self.cleaned_data.get('role', 'personnel')
            user.groups.clear()
            user.is_staff = role in ['admin', 'superuser', 'armorer']
            user.is_superuser = (role == 'superuser')
            user.save()
            
            if role == 'admin':
                Group.objects.get_or_create(name='Admin')[0].user_set.add(user)
            elif role == 'armorer':
                Group.objects.get_or_create(name='Armorer')[0].user_set.add(user)
            
            # Refresh user to get latest profile state after post_save signals
            user.refresh_from_db()
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.group = self.cleaned_data.get('group', 'HAS')
            profile.phone_number = self.cleaned_data.get('phone_number', '')
            profile.is_armorer = (role == 'armorer')
            if self.cleaned_data.get('profile_picture'):
                profile.profile_picture = self.cleaned_data['profile_picture']
            profile.save()
        
        elif operation_type in ['edit_user', 'edit_both']:
            user = User.objects.get(id=self.cleaned_data['edit_user_id'])
            user.username = self.cleaned_data['username']
            
            # For edit_both, prefer personnel data for names
            if operation_type == 'edit_both':
                user.first_name = self.cleaned_data.get('first_name') or self.cleaned_data.get('firstname', '')
                user.last_name = self.cleaned_data.get('last_name') or self.cleaned_data.get('surname', '')
            else:
                user.first_name = self.cleaned_data.get('first_name', '')
                user.last_name = self.cleaned_data.get('last_name', '')
            
            user.email = self.cleaned_data.get('email', '')
            user.is_active = self.cleaned_data.get('is_active', True)
            
            if self.cleaned_data.get('password'):
                user.set_password(self.cleaned_data['password'])
            
            role = self.cleaned_data.get('role', 'personnel')
            user.groups.clear()
            user.is_staff = role in ['admin', 'superuser', 'armorer']
            user.is_superuser = (role == 'superuser')
            user.save()
            
            if role == 'admin':
                Group.objects.get_or_create(name='Admin')[0].user_set.add(user)
            elif role == 'armorer':
                Group.objects.get_or_create(name='Armorer')[0].user_set.add(user)
            
            # Refresh user to get latest profile state after post_save signals
            user.refresh_from_db()
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.group = self.cleaned_data.get('group', 'HAS')
            profile.phone_number = self.cleaned_data.get('phone_number', '')
            profile.is_armorer = (role == 'armorer')
            if self.cleaned_data.get('profile_picture'):
                profile.profile_picture = self.cleaned_data['profile_picture']
            profile.save()
        
        if operation_type in ['create_personnel_only', 'create_user_with_personnel']:
            # Check if we're reactivating a soft-deleted personnel
            existing_personnel = self.cleaned_data.get('_reactivate_personnel')
            
            if existing_personnel:
                # Reactivate existing personnel with new data
                personnel = existing_personnel
                personnel.surname = self.cleaned_data['surname']
                personnel.firstname = self.cleaned_data['firstname']
                personnel.middle_initial = self.cleaned_data.get('middle_initial', '')
                personnel.rank = self.cleaned_data['rank']
                personnel.serial = self.cleaned_data['serial']
                personnel.group = self.cleaned_data['personnel_group']
                personnel.tel = self.cleaned_data['tel']
                personnel.status = self.cleaned_data.get('personnel_status', 'Active')
                personnel.user = user
                
                # Clear soft delete
                personnel.deleted_at = None
                
                # Update classification
                rank = self.cleaned_data['rank']
                officer_ranks = [r[0] for r in Personnel.RANKS_OFFICER]
                personnel.classification = 'OFFICER' if rank in officer_ranks else 'SUPERUSER' if (user and user.is_superuser) else 'ENLISTED PERSONNEL'
                
                if self.cleaned_data.get('personnel_picture'):
                    personnel.picture = self.cleaned_data['personnel_picture']
                personnel.save()
                
                # Reactivate QR code
                from qr_manager.models import QRCodeImage
                qr_code = QRCodeImage.all_objects.filter(qr_type='personnel', reference_id=personnel.id).first()
                if qr_code:
                    qr_code.reactivate()
            else:
                # Create new personnel
                rank = self.cleaned_data['rank']
                officer_ranks = [r[0] for r in Personnel.RANKS_OFFICER]
                classification = 'OFFICER' if rank in officer_ranks else 'SUPERUSER' if (user and user.is_superuser) else 'ENLISTED PERSONNEL'
                
                personnel = Personnel.objects.create(
                    surname=self.cleaned_data['surname'],
                    firstname=self.cleaned_data['firstname'],
                    middle_initial=self.cleaned_data.get('middle_initial', ''),
                    rank=rank if not (user and user.is_superuser) else None,
                    serial=self.cleaned_data['serial'],
                    group=self.cleaned_data['personnel_group'],
                    tel=self.cleaned_data['tel'],
                    status=self.cleaned_data.get('personnel_status', 'Active'),
                    classification=classification,
                    user=user
                )
                if self.cleaned_data.get('personnel_picture'):
                    personnel.picture = self.cleaned_data['personnel_picture']
                personnel.save()
        
        elif operation_type in ['edit_personnel', 'edit_both']:
            personnel = Personnel.objects.get(id=self.cleaned_data['edit_personnel_id'])
            personnel.surname = self.cleaned_data['surname']
            personnel.firstname = self.cleaned_data['firstname']
            personnel.middle_initial = self.cleaned_data.get('middle_initial', '')
            personnel.rank = self.cleaned_data['rank']
            personnel.serial = self.cleaned_data['serial']
            personnel.group = self.cleaned_data['personnel_group']
            personnel.tel = self.cleaned_data['tel']
            personnel.status = self.cleaned_data.get('personnel_status', 'Active')
            
            officer_ranks = [r[0] for r, _ in Personnel.RANKS_OFFICER]
            personnel.classification = 'OFFICER' if personnel.rank in officer_ranks else 'SUPERUSER' if (personnel.user and personnel.user.is_superuser) else 'ENLISTED PERSONNEL'
            if personnel.user and personnel.user.is_superuser:
                personnel.rank = None
            
            if self.cleaned_data.get('personnel_picture'):
                personnel.picture = self.cleaned_data['personnel_picture']
            personnel.save()
        
        return user, personnel


# === UTILITY FORMS ===

class ItemRegistrationForm(forms.ModelForm):
    """Form for registering inventory items"""
    class Meta:
        model = Item
        fields = ['item_type', 'serial', 'description', 'condition', 'status']
        widgets = {
            'item_type': forms.Select(attrs={'class': 'form-control'}),
            'serial': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'condition': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }

    def clean_serial(self):
        serial = self.cleaned_data['serial']
        if Item.objects.filter(serial=serial).exists():
            raise ValidationError('This serial number already exists.')
        return serial


class ItemEditForm(forms.ModelForm):
    """Form for editing existing inventory items"""
    class Meta:
        model = Item
        fields = ['item_type', 'serial', 'description', 'condition', 'status']
        widgets = {
            'item_type': forms.Select(attrs={'class': 'form-control'}),
            'serial': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'condition': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Store original serial for validation
        self.original_serial = self.instance.serial if self.instance and self.instance.pk else None

    def clean_serial(self):
        serial = self.cleaned_data['serial']
        # Allow keeping the same serial, but check for duplicates if changed
        if serial != self.original_serial:
            if Item.objects.filter(serial=serial).exists():
                raise ValidationError('This serial number already exists.')
        return serial


class SystemSettingsForm(forms.Form):
    """Form for system-wide settings"""
    system_name = forms.CharField(max_length=100, initial='Armguard System', widget=forms.TextInput(attrs={'class': 'form-control'}))
    max_users = forms.IntegerField(initial=100, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    enable_notifications = forms.BooleanField(initial=True, required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))


class PersonnelRegistrationForm(forms.ModelForm):
    """Legacy form - kept for backward compatibility. Use UniversalForm instead."""
    class Meta:
        model = Personnel
        fields = ['surname', 'firstname', 'middle_initial', 'rank', 'serial', 'group', 'tel', 'picture']
        widgets = {
            'surname': forms.TextInput(attrs={'class': 'form-control'}),
            'firstname': forms.TextInput(attrs={'class': 'form-control'}),
            'middle_initial': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '1'}),
            'rank': forms.Select(attrs={'class': 'form-control'}),
            'serial': forms.TextInput(attrs={'class': 'form-control'}),
            'group': forms.Select(attrs={'class': 'form-control'}),
            'tel': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '13'}),
            'picture': forms.FileInput(attrs={'class': 'form-control-file'}),
        }
