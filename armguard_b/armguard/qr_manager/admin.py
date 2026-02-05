"""
QR Code Admin Configuration
"""
from django.contrib import admin
from .models import QRCodeImage


@admin.register(QRCodeImage)
class QRCodeImageAdmin(admin.ModelAdmin):
    """Admin interface for QR Codes"""
    
    list_display = ['qr_type', 'reference_id', 'qr_data', 'created_at']
    list_filter = ['qr_type', 'created_at']
    search_fields = ['reference_id', 'qr_data']
    readonly_fields = ['qr_image', 'created_at', 'updated_at']

