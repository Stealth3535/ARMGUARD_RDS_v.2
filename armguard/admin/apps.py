from django.apps import AppConfig


class AdminConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'admin'
    label = 'admin_app'  # Use admin_app to avoid conflicts with django.contrib.admin
    verbose_name = 'Custom Admin Panel'
