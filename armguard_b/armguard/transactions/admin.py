"""
Transactions Admin Configuration
"""
from django.contrib import admin
from .models import Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    """Admin interface for Transactions"""
    
    list_display = ['id', 'personnel', 'item', 'action', 'date_time', 'issued_by', 'duty_type']
    list_filter = ['action', 'date_time', 'issued_by']
    search_fields = ['personnel__surname', 'personnel__firstname', 'item__serial', 'notes', 'issued_by__username']
    readonly_fields = ['created_at']
    date_hierarchy = 'date_time'
    
    fieldsets = (
        ('Transaction Information', {
            'fields': ('personnel', 'item', 'action', 'date_time', 'issued_by')
        }),
        ('Withdrawal Details', {
            'fields': ('duty_type', 'mags', 'rounds', 'notes'),
            'classes': ('collapse',)
        }),
        ('System Information', {
            'fields': ('created_at',)
        }),
    )

