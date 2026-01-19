"""
Personnel Admin Configuration
"""
from django.contrib import admin
from .models import Personnel


@admin.register(Personnel)
class PersonnelAdmin(admin.ModelAdmin):
    """Admin interface for Personnel"""
    
    list_display = ['id', 'get_full_name', 'rank', 'serial', 'office', 'status', 'registration_date']
    list_filter = ['status', 'rank', 'office', 'registration_date']
    search_fields = ['surname', 'firstname', 'serial', 'id']
    readonly_fields = ['id', 'qr_code', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Personal Information', {
            'fields': ('surname', 'firstname', 'middle_initial', 'picture')
        }),
        ('Military Information', {
            'fields': ('rank', 'serial', 'office')
        }),
        ('Contact Information', {
            'fields': ('tel',)
        }),
        ('System Information', {
            'fields': ('id', 'qr_code', 'status', 'registration_date', 'created_at', 'updated_at')
        }),
    )
    
    def get_full_name(self, obj):
        return obj.get_full_name()
    get_full_name.short_description = 'Full Name'

