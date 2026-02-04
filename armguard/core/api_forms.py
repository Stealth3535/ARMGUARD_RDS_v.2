"""
Enhanced API input validation forms
"""
from django import forms
from django.core.exceptions import ValidationError
import re

class TransactionCreateForm(forms.Form):
    """Secure form for transaction creation API"""
    personnel_id = forms.CharField(
        max_length=50, 
        required=True,
        help_text="Personnel ID (e.g., PE-123456 or QR reference)"
    )
    item_id = forms.CharField(
        max_length=50, 
        required=True,
        help_text="Item ID (e.g., IP-123456 or QR reference)"
    )
    action = forms.ChoiceField(
        choices=[('Take', 'Take'), ('Return', 'Return')],
        required=True
    )
    notes = forms.CharField(
        max_length=500, 
        required=False,
        strip=True
    )
    mags = forms.IntegerField(
        min_value=0, 
        max_value=999, 
        required=False,
        initial=0
    )
    rounds = forms.IntegerField(
        min_value=0, 
        max_value=9999, 
        required=False,
        initial=0
    )
    duty_type = forms.CharField(
        max_length=50,
        required=False,
        strip=True
    )
    
    def clean_personnel_id(self):
        personnel_id = self.cleaned_data['personnel_id']
        # Validate format (PE-XXXXXX or QR reference)
        if not re.match(r'^(PE-\d{6}|[A-Za-z0-9\-_]{3,50})$', personnel_id):
            raise ValidationError('Invalid personnel ID format')
        return personnel_id
    
    def clean_item_id(self):
        item_id = self.cleaned_data['item_id']
        # Validate format (IP-XXXXXX or QR reference)
        if not re.match(r'^(IP-\d{6}|[A-Za-z0-9\-_]{3,50})$', item_id):
            raise ValidationError('Invalid item ID format')
        return item_id
    
    def clean_notes(self):
        notes = self.cleaned_data.get('notes', '')
        if notes:
            # Remove potentially dangerous content
            notes = re.sub(r'[<>&"\']', '', notes)
            # Limit length
            if len(notes) > 500:
                notes = notes[:500]
        return notes

class PersonnelLookupForm(forms.Form):
    """Form for personnel API lookup"""
    personnel_id = forms.CharField(
        max_length=50,
        required=True
    )
    
    def clean_personnel_id(self):
        personnel_id = self.cleaned_data['personnel_id']
        if not re.match(r'^(PE-\d{6}|[A-Za-z0-9\-_]{3,50})$', personnel_id):
            raise ValidationError('Invalid personnel ID format')
        return personnel_id

class ItemLookupForm(forms.Form):
    """Form for item API lookup"""
    item_id = forms.CharField(
        max_length=50,
        required=True
    )
    
    def clean_item_id(self):
        item_id = self.cleaned_data['item_id']
        if not re.match(r'^(IP-\d{6}|[A-Za-z0-9\-_]{3,50})$', item_id):
            raise ValidationError('Invalid item ID format')
        return item_id