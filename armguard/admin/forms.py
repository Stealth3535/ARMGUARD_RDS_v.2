"""
Admin Forms - Centralized Registration and User Management
"""
from django import forms
from django.contrib.auth.models import User, Group
from django.core.exceptions import ValidationError
from django.contrib.auth.forms import UserCreationForm
from personnel.models import Personnel
from inventory.models import Item
from users.models import UserProfile
from users.forms import UserRegistrationForm


class PersonnelRegistrationForm(forms.ModelForm):
    """Traditional Personnel Registration Form - Centralized Version"""
    
    # Personal Information
    surname = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'})
    )
    firstname = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'})
    )
    middle_initial = forms.CharField(
        max_length=10,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'M.I. (Optional)'})
    )
    
    # Military Information
    rank = forms.ChoiceField(
        choices=Personnel.ALL_RANKS,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    serial = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Serial Number'})
    )
    office = forms.ChoiceField(
        choices=Personnel.OFFICE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    # Contact Information
    tel = forms.CharField(
        max_length=13,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': '+639XXXXXXXXX',
            'pattern': '\+639\d{9}'
        })
    )
    
    # Status and Photo
    status = forms.ChoiceField(
        choices=Personnel.STATUS_CHOICES,
        initial=Personnel.STATUS_ACTIVE,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    picture = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control-file'})
    )
    
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

    def clean_serial(self):
        serial = self.cleaned_data['serial']
        # Check if serial already exists
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
        personnel = super().save(commit=False)
        
        # Generate unique ID for personnel
        from datetime import datetime
        today = datetime.now().strftime('%d%m%y')
        base_id = f"PE-{personnel.serial}{today}"
        personnel.id = base_id
        
        # Generate QR code
        personnel.qr_code = base_id
        
        if commit:
            personnel.save()
            
            # Create user account if requested
            if self.cleaned_data.get('create_user_account'):
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
                
                # Generate QR code for both personnel and user
                from qr_manager.models import QRCodeImage
                QRCodeImage.objects.create(
                    qr_type=QRCodeImage.TYPE_PERSONNEL,
                    reference_id=personnel.id,
                    data_content=f"Personnel: {personnel.get_full_name()}\nRank: {personnel.rank}\nSerial: {personnel.serial}"
                )
        
        return personnel


class UniversalRegistrationForm(forms.Form):
    """Universal form for registering users with optional personnel linking"""
    
    # Registration Type
    REGISTRATION_TYPES = [
        ('user_only', 'User Account Only'),
        ('personnel_only', 'Personnel Record Only'), 
        ('user_with_personnel', 'User Account + Personnel Record'),
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
        if registration_type in ['user_only', 'user_with_personnel']:
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
        
        return cleaned_data
    
    def save(self, commit=True):
        """Save based on registration type"""
        registration_type = self.cleaned_data['registration_type']
        user = None
        personnel = None
        
        if registration_type in ['user_only', 'user_with_personnel']:
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
            profile = user.userprofile
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
        
        return user, personnel


# Keep simplified forms for specific use cases
class AdminUserForm(forms.ModelForm):
    """Simplified form for user-only registration"""
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
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # If this is an edit form (instance exists), populate additional fields
        if self.instance and self.instance.pk:
            try:
                profile = self.instance.userprofile
                self.initial['department'] = profile.department or ''
                self.initial['phone_number'] = profile.phone_number or ''
                self.initial['badge_number'] = profile.badge_number or ''
                
                # Determine role based on groups and permissions
                if self.instance.is_superuser:
                    self.initial['role'] = 'superuser'
                elif self.instance.groups.filter(name='Admin').exists():
                    self.initial['role'] = 'admin'
                elif self.instance.groups.filter(name='Armorer').exists():
                    self.initial['role'] = 'armorer'
                else:
                    self.initial['role'] = 'regular'
            except:
                # If no profile exists, use defaults
                pass
    
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
    
    def save(self, commit=True):
        """Override save to handle additional fields"""
        user = super().save(commit=False)
        if commit:
            user.save()
        return user
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        
        # Check passwords match if provided
        if password and password != confirm_password:
            raise ValidationError("Passwords do not match.")
        
        # Check if password is required for new users
        if not self.instance.pk and not password:
            raise ValidationError("Password is required for new users.")
        
        return cleaned_data


class ArmorerRegistrationForm(UserRegistrationForm):
    """Form for registering armorers - extends the base UserRegistrationForm"""
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
        # Ensure our additional fields also get the form-control class
        self.fields['department'].widget.attrs.update({'class': 'form-control'})
        self.fields['phone_number'].widget.attrs.update({'class': 'form-control'})
        self.fields['badge_number'].widget.attrs.update({'class': 'form-control'})
        self.fields['profile_picture'].widget.attrs.update({'class': 'form-control-file'})
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_staff = True  # Armorers are staff
        
        if commit:
            user.save()
            
            # Update user profile with additional fields
            profile = user.userprofile
            profile.department = self.cleaned_data.get('department', '')
            profile.phone_number = self.cleaned_data.get('phone_number', '')
            profile.badge_number = self.cleaned_data.get('badge_number', '')
            profile.is_armorer = True
            
            # Handle profile picture upload
            if self.cleaned_data.get('profile_picture'):
                profile.profile_picture = self.cleaned_data['profile_picture']
            
            profile.save()
            
            # Add to Armorer group
            armorer_group, _ = Group.objects.get_or_create(name='Armorer')
            user.groups.add(armorer_group)
        
        return user


class PersonnelRegistrationForm(forms.ModelForm):
    """Form for registering personnel (without user accounts)"""
    class Meta:
        model = Personnel
        fields = ['surname', 'firstname', 'middle_initial', 'rank', 'serial', 'office', 'tel', 'picture']
        widgets = {
            'surname': forms.TextInput(attrs={'class': 'form-control'}),
            'firstname': forms.TextInput(attrs={'class': 'form-control'}),
            'middle_initial': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '1'}),
            'rank': forms.Select(attrs={'class': 'form-control'}),
            'serial': forms.TextInput(attrs={'class': 'form-control'}),
            'office': forms.TextInput(attrs={'class': 'form-control'}),
            'tel': forms.TextInput(attrs={'class': 'form-control'}),
            'picture': forms.FileInput(attrs={'class': 'form-control-file'}),
        }
    
    def clean_serial(self):
        serial = self.cleaned_data['serial']
        if Personnel.objects.filter(serial=serial).exists():
            if not self.instance.pk or self.instance.serial != serial:
                raise ValidationError('Personnel with this serial number already exists.')
        return serial
    
    def save(self, commit=True):
        personnel = super().save(commit=False)
        
        # Apply proper capitalization based on rank
        rank = personnel.rank
        is_officer = rank in [r[0] for r in Personnel.RANKS_OFFICER] if hasattr(Personnel, 'RANKS_OFFICER') else False
        
        if is_officer:
            personnel.surname = personnel.surname.upper()
            personnel.firstname = personnel.firstname.upper()
            if personnel.middle_initial:
                personnel.middle_initial = personnel.middle_initial.upper()
        else:
            personnel.surname = personnel.surname.title()
            personnel.firstname = personnel.firstname.title()
            if personnel.middle_initial:
                personnel.middle_initial = personnel.middle_initial.upper()
        
        personnel.rank = personnel.rank.upper()
        
        if commit:
            personnel.save()
        
        return personnel


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
