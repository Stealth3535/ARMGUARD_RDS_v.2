"""
ArmGuard - Consolidated Forms File
All form classes in one centralized location for easy management and maintenance.
"""
from django import forms
from django.contrib.auth.models import User, Group
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from personnel.models import Personnel
from inventory.models import Item
from transactions.models import Transaction
from users.models import UserProfile


# =============================================================================
# USER REGISTRATION FORMS
# =============================================================================

class UserRegistrationForm(UserCreationForm):
    """Base user registration form with profile picture"""
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    middle_initial = forms.CharField(
        max_length=1, 
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'maxlength': '1'}),
        help_text='Optional middle initial'
    )
    profile_picture = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control-file'}),
        help_text='Optional profile picture (JPG, PNG, or GIF format)'
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'middle_initial', 'email', 'password1', 'password2', 'profile_picture']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Apply form-control class to all fields
        self.fields['username'].widget.attrs.update({'class': 'form-control'})
        self.fields['first_name'].widget.attrs.update({'class': 'form-control'})
        self.fields['last_name'].widget.attrs.update({'class': 'form-control'})
        self.fields['middle_initial'].widget.attrs.update({'class': 'form-control'})
        self.fields['email'].widget.attrs.update({'class': 'form-control'})
        self.fields['password1'].widget.attrs.update({'class': 'form-control'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control'})
        self.fields['profile_picture'].widget.attrs.update({'class': 'form-control-file'})

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError('A user with this email already exists.')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']

        if commit:
            user.save()
            
            # Create or get user profile and handle profile picture
            profile, created = UserProfile.objects.get_or_create(user=user)
            if self.cleaned_data.get('profile_picture'):
                profile.profile_picture = self.cleaned_data['profile_picture']
                profile.save()

        return user


class UserProfileForm(forms.ModelForm):
    """Form for editing user profiles"""
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

    # Additional profile fields
    department = forms.CharField(
        max_length=100, 
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    phone_number = forms.CharField(
        max_length=15, 
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    badge_number = forms.CharField(
        max_length=50, 
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    profile_picture = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control-file'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and hasattr(self.instance, 'userprofile'):
            profile = self.instance.userprofile
            self.fields['department'].initial = profile.department
            self.fields['phone_number'].initial = profile.phone_number
            self.fields['badge_number'].initial = profile.badge_number

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.department = self.cleaned_data.get('department', '')
            profile.phone_number = self.cleaned_data.get('phone_number', '')
            profile.badge_number = self.cleaned_data.get('badge_number', '')
            
            if self.cleaned_data.get('profile_picture'):
                profile.profile_picture = self.cleaned_data['profile_picture']
            
            profile.save()
        return user


class ArmorerRegistrationForm(UserRegistrationForm):
    """Form for registering armorers with additional fields"""
    department = forms.CharField(
        max_length=100, 
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    phone_number = forms.CharField(
        max_length=15, 
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    badge_number = forms.CharField(
        max_length=50, 
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_staff = True  # Armorers are staff
        
        if commit:
            user.save()
            
            # Update user profile with additional fields
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.department = self.cleaned_data.get('department', '')
            profile.phone_number = self.cleaned_data.get('phone_number', '')
            profile.badge_number = self.cleaned_data.get('badge_number', '')
            profile.is_armorer = True
            
            if self.cleaned_data.get('profile_picture'):
                profile.profile_picture = self.cleaned_data['profile_picture']
            
            profile.save()
            
            # Add to Armorer group
            armorer_group, _ = Group.objects.get_or_create(name='Armorer')
            user.groups.add(armorer_group)
        
        return user


class AdminUserForm(forms.ModelForm):
    """Form for creating/editing admin users"""
    ROLE_CHOICES = [
        ('regular', 'Regular User'),
        ('armorer', 'Armorer'),
        ('admin', 'Administrator'),
        ('superuser', 'Superuser'),
    ]
    
    role = forms.ChoiceField(choices=ROLE_CHOICES, initial='regular')
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=False,
        help_text="Leave blank to keep existing password (when editing)"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=False,
        help_text="Confirm the password"
    )
    
    # Additional profile fields
    department = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    phone_number = forms.CharField(
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    badge_number = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    profile_picture = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control-file'})
    )
    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'is_active']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if password and password != confirm_password:
            raise ValidationError("Passwords do not match.")
        
        if not self.instance.pk and not password:
            raise ValidationError("Password is required for new users.")
        
        return cleaned_data


# =============================================================================
# PERSONNEL FORMS
# =============================================================================

class PersonnelRegistrationForm(forms.ModelForm):
    """Form for registering military personnel"""
    
    # Optional User Account Creation
    create_user_account = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text='Check this to create a user account for this personnel'
    )
    
    # User Account Fields (conditional)
    username = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username (optional)'})
    )
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email (optional)'})
    )
    password1 = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'})
    )
    password2 = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm Password'})
    )
    
    user_role = forms.ChoiceField(
        choices=[
            ('regular', 'Regular User'),
            ('armorer', 'Armorer'),
            ('admin', 'Administrator'),
        ],
        initial='regular',
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Personnel
        fields = ['surname', 'firstname', 'middle_initial', 'rank', 'serial', 'office', 'tel', 'status', 'picture']
        widgets = {
            'surname': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}),
            'firstname': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}),
            'middle_initial': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'M.I. (Optional)'}),
            'rank': forms.Select(attrs={'class': 'form-control'}),
            'serial': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Serial Number'}),
            'office': forms.Select(attrs={'class': 'form-control'}),
            'tel': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+639XXXXXXXXX', 'pattern': r'\+639\d{9}'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'picture': forms.FileInput(attrs={'class': 'form-control-file'}),
        }

    def clean_serial(self):
        serial = self.cleaned_data['serial']
        if Personnel.objects.filter(serial=serial).exists():
            raise ValidationError('This serial number is already registered.')
        return serial

    def clean_tel(self):
        tel = self.cleaned_data['tel']
        if tel and not tel.startswith('+639'):
            raise ValidationError('Phone number must start with +639')
        if tel and len(tel) != 13:
            raise ValidationError('Phone number must be exactly 13 digits including +639')
        return tel

    def clean(self):
        cleaned_data = super().clean()
        create_user = cleaned_data.get('create_user_account')
        
        if create_user:
            username = cleaned_data.get('username')
            password1 = cleaned_data.get('password1')
            password2 = cleaned_data.get('password2')
            
            if not username:
                raise ValidationError('Username is required when creating user account')
            if not password1:
                raise ValidationError('Password is required when creating user account')
            if password1 != password2:
                raise ValidationError('Passwords do not match')
            if User.objects.filter(username=username).exists():
                raise ValidationError('Username already exists')
        
        return cleaned_data

    def save(self, commit=True):
        personnel = super().save(commit=commit)
        
        if commit and self.cleaned_data.get('create_user_account'):
            # Create user account
            user = User.objects.create_user(
                username=self.cleaned_data['username'],
                email=self.cleaned_data.get('email', ''),
                password=self.cleaned_data['password1'],
                first_name=personnel.firstname,
                last_name=personnel.surname
            )
            
            # Assign role
            role = self.cleaned_data.get('user_role', 'regular')
            if role == 'admin':
                admin_group, _ = Group.objects.get_or_create(name='Admin')
                user.groups.add(admin_group)
                user.is_staff = True
            elif role == 'armorer':
                armorer_group, _ = Group.objects.get_or_create(name='Armorer')
                user.groups.add(armorer_group)
            else:
                user_group, _ = Group.objects.get_or_create(name='User')
                user.groups.add(user_group)
            
            user.save()
            
            # Link personnel to user
            personnel.user = user
            personnel.save()
        
        return personnel


# =============================================================================
# INVENTORY FORMS
# =============================================================================

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
            if not self.instance.pk or self.instance.serial != serial:
                raise ValidationError('Item with this serial number already exists.')
        return serial


# =============================================================================
# TRANSACTION FORMS
# =============================================================================

class TransactionForm(forms.ModelForm):
    """Form for recording transactions (take/return)"""
    
    class Meta:
        model = Transaction
        fields = ['personnel', 'item', 'action', 'mags', 'rounds', 'duty_type', 'notes']
        widgets = {
            'personnel': forms.Select(attrs={
                'class': 'form-control',
                'id': 'personnel-select'
            }),
            'item': forms.Select(attrs={
                'class': 'form-control',
                'id': 'item-select'
            }),
            'action': forms.Select(attrs={
                'class': 'form-control',
                'id': 'action-select'
            }),
            'mags': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'id': 'mags-input'
            }),
            'rounds': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'id': 'rounds-input'
            }),
            'duty_type': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Duty Sentinel, Guard Duty',
                'id': 'duty-type-input'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Additional notes or remarks...'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter available items based on status
        self.fields['item'].queryset = Item.objects.filter(
            status__in=[Item.STATUS_AVAILABLE, Item.STATUS_ISSUED]
        )
        
        # Filter active personnel
        self.fields['personnel'].queryset = Personnel.objects.filter(
            status=Personnel.STATUS_ACTIVE
        )

    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        item = cleaned_data.get('item')
        
        if action and item:
            # Validate action against item status
            if action == Transaction.ACTION_TAKE:
                if item.status != Item.STATUS_AVAILABLE:
                    raise ValidationError(
                        f'Cannot take item. Current status: {item.status}. Item must be Available.'
                    )
            elif action == Transaction.ACTION_RETURN:
                if item.status != Item.STATUS_ISSUED:
                    raise ValidationError(
                        f'Cannot return item. Current status: {item.status}. Item must be Issued.'
                    )
        
        return cleaned_data

    def save(self, commit=True):
        transaction = super().save(commit=False)
        
        if commit:
            transaction.save()
            
            # Update item status based on action
            item = transaction.item
            if transaction.action == Transaction.ACTION_TAKE:
                item.status = Item.STATUS_ISSUED
            elif transaction.action == Transaction.ACTION_RETURN:
                item.status = Item.STATUS_AVAILABLE
            
            item.save()
        
        return transaction


# =============================================================================
# UNIVERSAL REGISTRATION FORM
# =============================================================================

class UniversalRegistrationForm(forms.Form):
    """Universal form for registering users with optional personnel linking"""
    
    # Registration Type
    REGISTRATION_TYPES = [
        ('user_only', 'User Account Only'),
        ('personnel_only', 'Personnel Record Only'), 
        ('user_with_personnel', 'User Account + Personnel Record'),
        ('link_existing', 'Link User to Existing Personnel'),
    ]
    
    registration_type = forms.ChoiceField(
        choices=REGISTRATION_TYPES,
        initial='user_with_personnel',
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'registrationType'}),
        help_text='Choose what type of record to create'
    )
    
    # User Role (for user accounts)
    ROLE_CHOICES = [
        ('regular', 'Regular User'),
        ('armorer', 'Armorer'),
        ('admin', 'Administrator'),
        ('superuser', 'Superuser'),
    ]
    
    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        initial='regular',
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    # === USER ACCOUNT FIELDS ===
    username = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=False,
        help_text="Password for user account"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=False,
        help_text="Confirm the password"
    )
    
    # User Profile fields
    department = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    phone_number = forms.CharField(
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    badge_number = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    profile_picture = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control-file'})
    )
    
    # === PERSONNEL FIELDS ===
    surname = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    firstname = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    middle_initial = forms.CharField(
        max_length=1,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'maxlength': '1'})
    )
    rank = forms.ChoiceField(
        choices=Personnel.ALL_RANKS,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    serial = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        help_text="Serial number (6 digits for enlisted, or O-XXXXXX for officers)"
    )
    office = forms.ChoiceField(
        choices=Personnel.OFFICE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    tel = forms.CharField(
        max_length=13,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        help_text="+639XXXXXXXXX"
    )
    personnel_status = forms.ChoiceField(
        choices=Personnel.STATUS_CHOICES,
        initial=Personnel.STATUS_ACTIVE,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    personnel_picture = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control-file'}),
        help_text='Personnel photo (JPG, PNG, or GIF format)'
    )
    
    # Link to existing personnel
    existing_personnel = forms.ModelChoiceField(
        queryset=Personnel.objects.filter(user__isnull=True),
        required=False,
        empty_label="Select personnel to link...",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    # Active status
    is_active = forms.BooleanField(
        initial=True,
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    def clean(self):
        cleaned_data = super().clean()
        registration_type = cleaned_data.get('registration_type')
        
        # Validate based on registration type
        if registration_type in ['user_only', 'user_with_personnel', 'link_existing']:
            # User account fields required
            required_user_fields = ['username', 'email', 'password', 'confirm_password']
            for field in required_user_fields:
                if not cleaned_data.get(field):
                    self.add_error(field, f'This field is required for {registration_type} registration.')
            
            # Check passwords match
            password = cleaned_data.get('password')
            confirm_password = cleaned_data.get('confirm_password')
            if password and password != confirm_password:
                self.add_error('confirm_password', "Passwords do not match.")
            
            # Check username uniqueness
            username = cleaned_data.get('username')
            if username and User.objects.filter(username=username).exists():
                self.add_error('username', "Username already exists.")
        
        if registration_type in ['personnel_only', 'user_with_personnel']:
            # Personnel fields required
            required_personnel_fields = ['surname', 'firstname', 'rank', 'serial', 'office', 'tel']
            for field in required_personnel_fields:
                if not cleaned_data.get(field):
                    self.add_error(field, f'This field is required for {registration_type} registration.')
            
            # Check serial uniqueness
            serial = cleaned_data.get('serial')
            if serial and Personnel.objects.filter(serial=serial).exists():
                self.add_error('serial', "Personnel with this serial number already exists.")
        
        if registration_type == 'link_existing':
            if not cleaned_data.get('existing_personnel'):
                self.add_error('existing_personnel', 'Please select personnel to link to the user account.')
        
        return cleaned_data
    
    def save(self, commit=True):
        """Save based on registration type"""
        registration_type = self.cleaned_data['registration_type']
        user = None
        personnel = None
        
        if registration_type in ['user_only', 'user_with_personnel', 'link_existing']:
            # Create user account
            user = User.objects.create_user(
                username=self.cleaned_data['username'],
                email=self.cleaned_data['email'],
                password=self.cleaned_data['password'],
                first_name=self.cleaned_data.get('firstname', ''),
                last_name=self.cleaned_data.get('surname', ''),
                is_active=self.cleaned_data.get('is_active', True)
            )
            
            # Set role-based permissions
            role = self.cleaned_data.get('role', 'regular')
            if role == 'admin':
                user.is_staff = True
                user.is_superuser = False
            elif role == 'superuser':
                user.is_staff = True
                user.is_superuser = True
            elif role == 'armorer':
                user.is_staff = True
                user.is_superuser = False
            
            user.save()
            
            # Update user profile
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.department = self.cleaned_data.get('department', '')
            profile.phone_number = self.cleaned_data.get('phone_number', '')
            profile.badge_number = self.cleaned_data.get('badge_number', '')
            
            if role == 'armorer':
                profile.is_armorer = True
            
            # Handle profile picture upload
            if self.cleaned_data.get('profile_picture'):
                profile.profile_picture = self.cleaned_data['profile_picture']
            
            profile.save()
            
            # Add to appropriate groups
            if role == 'admin':
                admin_group, _ = Group.objects.get_or_create(name='Admin')
                user.groups.add(admin_group)
            elif role == 'armorer':
                armorer_group, _ = Group.objects.get_or_create(name='Armorer')
                user.groups.add(armorer_group)
        
        if registration_type in ['personnel_only', 'user_with_personnel']:
            # Create personnel record
            personnel = Personnel(
                surname=self.cleaned_data['surname'],
                firstname=self.cleaned_data['firstname'],
                middle_initial=self.cleaned_data.get('middle_initial', ''),
                rank=self.cleaned_data['rank'],
                serial=self.cleaned_data['serial'],
                office=self.cleaned_data['office'],
                tel=self.cleaned_data['tel'],
                status=self.cleaned_data.get('personnel_status', Personnel.STATUS_ACTIVE),
            )
            
            # Handle personnel picture upload
            if self.cleaned_data.get('personnel_picture'):
                personnel.picture = self.cleaned_data['personnel_picture']
            
            # Link user if creating both
            if user:
                personnel.user = user
            
            if commit:
                personnel.save()
        
        elif registration_type == 'link_existing':
            # Link user to existing personnel
            personnel = self.cleaned_data['existing_personnel']
            personnel.user = user
            if commit:
                personnel.save()
        
        return user, personnel


# =============================================================================
# SYSTEM SETTINGS FORM
# =============================================================================

class SystemSettingsForm(forms.Form):
    """Form for system configuration settings"""
    site_name = forms.CharField(
        max_length=100,
        initial='ArmGuard',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    debug_mode = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    max_login_attempts = forms.IntegerField(
        min_value=1,
        max_value=10,
        initial=5,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    session_timeout = forms.IntegerField(
        min_value=5,
        max_value=1440,  # 24 hours
        initial=60,
        help_text="Session timeout in minutes",
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    enable_email_notifications = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    def clean_session_timeout(self):
        timeout = self.cleaned_data['session_timeout']
        return timeout * 60  # Convert to seconds


# =============================================================================
# EXPORT: All forms available from this module
# =============================================================================

__all__ = [
    # User Forms
    'UserRegistrationForm',
    'UserProfileForm', 
    'ArmorerRegistrationForm',
    'AdminUserForm',
    
    # Personnel Forms
    'PersonnelRegistrationForm',
    
    # Inventory Forms
    'ItemRegistrationForm',
    
    # Transaction Forms
    'TransactionForm',
    
    # Universal Forms
    'UniversalRegistrationForm',
    
    # System Forms
    'SystemSettingsForm',
]