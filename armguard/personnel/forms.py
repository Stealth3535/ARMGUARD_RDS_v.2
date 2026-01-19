"""
Personnel Forms - Search and Quick Operations Only
Note: Main personnel registration is now handled by admin.forms.UniversalRegistrationForm
"""
from django import forms
from django.core.exceptions import ValidationError
from .models import Personnel


class PersonnelSearchForm(forms.Form):
    """Form for searching personnel records"""
    search_query = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by name, rank, serial, or office...',
            'id': 'search-input'
        })
    )
    
    status = forms.ChoiceField(
        choices=[('', 'All Status')] + Personnel.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    rank_type = forms.ChoiceField(
        choices=[
            ('', 'All Ranks'),
            ('officer', 'Officers'),
            ('enlisted', 'Enlisted'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    office = forms.ChoiceField(
        choices=[('', 'All Offices')] + Personnel.OFFICE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )


class PersonnelQuickEditForm(forms.ModelForm):
    """Form for quick editing of personnel information (admin only)"""
    class Meta:
        model = Personnel
        fields = ['rank', 'office', 'tel', 'status', 'picture']
        widgets = {
            'rank': forms.Select(attrs={'class': 'form-control'}),
            'office': forms.Select(attrs={'class': 'form-control'}),
            'tel': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'picture': forms.FileInput(attrs={'class': 'form-control-file'}),
        }
    
    def clean_tel(self):
        tel = self.cleaned_data['tel']
        if tel and not tel.startswith('+639'):
            raise ValidationError('Telephone number must start with +639')
        if tel and len(tel) != 13:
            raise ValidationError('Telephone number must be 13 digits including +639')
        return tel
