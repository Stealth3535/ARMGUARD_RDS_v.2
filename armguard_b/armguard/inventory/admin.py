"""
Inventory Admin Configuration
"""
from django.contrib import admin
from .models import Item


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    """Admin interface for Items"""
    
    list_display = ['id', 'item_type', 'serial', 'status', 'condition', 'registration_date']
    list_filter = ['status', 'condition', 'item_type', 'registration_date']
    search_fields = ['serial', 'id', 'description']
    readonly_fields = ['id', 'qr_code', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Item Information', {
            'fields': ('item_type', 'serial', 'description')
        }),
        ('Status', {
            'fields': ('status', 'condition')
        }),
        ('System Information', {
            'fields': ('id', 'qr_code', 'registration_date', 'created_at', 'updated_at')
        }),
    )

