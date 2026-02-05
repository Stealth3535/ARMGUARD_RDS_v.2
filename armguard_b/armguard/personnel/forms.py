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
            'placeholder': 'Search by name, rank, serial, or group...',
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
    
    group = forms.ChoiceField(
        choices=[('', 'All Groups')] + Personnel.GROUP_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )


class PersonnelQuickEditForm(forms.ModelForm):
    """Form for quick editing of personnel information (admin only)"""
    class Meta:
        model = Personnel
        fields = ['rank', 'group', 'tel', 'status', 'picture']
        widgets = {
            'rank': forms.Select(attrs={'class': 'form-control'}),
            'group': forms.Select(attrs={'class': 'form-control'}),
            'tel': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '13'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'picture': forms.FileInput(attrs={'class': 'form-control-file'}),
        }
    
    def clean_tel(self):
        tel = self.cleaned_data.get('tel')
        if tel:
            # Auto-convert 09XXXXXXXXX to +639XXXXXXXXX
            if tel.startswith('09') and len(tel) == 11 and tel.isdigit():
                tel = '+63' + tel[1:]
                self.cleaned_data['tel'] = tel
            elif not tel.startswith('+639') or len(tel) != 13:
                raise ValidationError('Phone number must be in +639XXXXXXXXX format or 09XXXXXXXXX format.')
        return tel
