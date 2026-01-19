from django import forms
from .models import Transaction
from personnel.models import Personnel
from inventory.models import Item


class TransactionForm(forms.ModelForm):
    """Form for creating transactions"""
    
    # Mode selection (not stored in database)
    mode = forms.ChoiceField(
        choices=[
            ('normal', 'Normal Mode'),
            ('defcon', 'Defcon Mode')
        ],
        initial='normal',
        widget=forms.Select(attrs={
            'class': 'form-control',
            'id': 'modeSelect'
        })
    )
    
    # Action selection
    action = forms.ChoiceField(
        choices=[
            ('Take', 'Withdraw Item'),
            ('Return', 'Return Item')
        ],
        initial='Take',
        widget=forms.Select(attrs={
            'class': 'form-control',
            'id': 'actionSelect'
        })
    )
    
    # Personnel and Item inputs
    personnel_id = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'id': 'personnelInput',
            'placeholder': 'Scan or enter Personnel ID',
            'autocomplete': 'off'
        })
    )
    
    item_id = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'id': 'itemInput',
            'placeholder': 'Scan or enter Item ID',
            'autocomplete': 'off'
        })
    )
    
    # Duty Type dropdown
    duty_type = forms.ChoiceField(
        choices=[
            ('', 'Select Duty Type'),
            ('Duty Sentinel', 'Duty Sentinel'),
            ('Duty Security', 'Duty Security'),
            ('Vigil', 'Vigil'),
            ('Guard Duty', 'Guard Duty'),
            ('Patrol', 'Patrol'),
            ('Training', 'Training'),
        ],
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control',
            'id': 'dutyType'
        })
    )
    
    # Mags and Rounds
    mags = forms.IntegerField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'id': 'mags',
            'placeholder': 'Number of mags',
            'min': '0'
        })
    )
    
    rounds = forms.IntegerField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'id': 'rounds',
            'placeholder': 'Rounds of ammo',
            'min': '0'
        })
    )
    
    # Notes
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'id': 'notes',
            'placeholder': 'Optional notes...',
            'rows': '3'
        })
    )
    
    class Meta:
        model = Transaction
        fields = ['action', 'duty_type', 'mags', 'rounds', 'notes']
    
    def clean_personnel_id(self):
        """Validate and get personnel instance"""
        personnel_id = self.cleaned_data.get('personnel_id')
        try:
            personnel = Personnel.objects.get(id=personnel_id)
            return personnel
        except Personnel.DoesNotExist:
            raise forms.ValidationError(f"Personnel with ID '{personnel_id}' not found.")
    
    def clean_item_id(self):
        """Validate and get item instance"""
        item_id = self.cleaned_data.get('item_id')
        try:
            item = Item.objects.get(id=item_id)
            return item
        except Item.DoesNotExist:
            raise forms.ValidationError(f"Item with ID '{item_id}' not found.")
    
    def clean(self):
        """Additional validation for action and item status"""
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        item = cleaned_data.get('item_id')
        
        if item and action:
            if action == 'Take' and item.status != 'Available':
                raise forms.ValidationError(
                    f"Cannot withdraw item. Current status: {item.status}. Item must be Available."
                )
            elif action == 'Return' and item.status != 'Issued':
                raise forms.ValidationError(
                    f"Cannot return item. Current status: {item.status}. Item must be Issued."
                )
        
        return cleaned_data


class TransactionFilterForm(forms.Form):
    """Form for filtering transactions"""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'search-input',
            'id': 'searchInput',
            'placeholder': '🔍 Search by personnel name, rank, or item...'
        })
    )
    
    action_filter = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'All Actions'),
            ('Take', 'Withdraw'),
            ('Return', 'Return')
        ],
        widget=forms.Select(attrs={
            'class': 'form-control form-select',
            'id': 'actionFilter'
        })
    )
    
    duty_filter = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'All Duty Types'),
            ('Duty Sentinel', 'Duty Sentinel'),
            ('Duty Security', 'Duty Security'),
            ('Vigil', 'Vigil'),
            ('Guard Duty', 'Guard Duty'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-control form-select',
            'id': 'dutyFilterDropdown'
        })
    )
