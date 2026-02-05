"""
Transaction Models for ArmGuard
Based on APP/app/backend/database.py transactions table
"""
from django.db import models
from django.utils import timezone
from django.conf import settings
from personnel.models import Personnel
from inventory.models import Item


class Transaction(models.Model):
    """Transaction model - Records of item withdrawals and returns"""
    
    # Action choices
    ACTION_TAKE = 'Take'
    ACTION_RETURN = 'Return'
    
    ACTION_CHOICES = [
        (ACTION_TAKE, 'Take/Withdraw'),
        (ACTION_RETURN, 'Return'),
    ]
    
    # Auto-increment ID
    id = models.AutoField(primary_key=True)
    
    # Foreign Keys
    personnel = models.ForeignKey(
        Personnel,
        on_delete=models.PROTECT,
        related_name='transactions',
        db_column='personnel_id'
    )
    item = models.ForeignKey(
        Item,
        on_delete=models.PROTECT,
        related_name='transactions',
        db_column='item_id'
    )
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='issued_transactions',
        help_text="User who processed this transaction"
    )
    
    # Transaction Details
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    date_time = models.DateTimeField(default=timezone.now)
    
    # Additional fields for withdrawals
    mags = models.IntegerField(
        default=0,
        blank=True,
        null=True,
        help_text="Number of magazines issued"
    )
    rounds = models.IntegerField(
        default=0,
        blank=True,
        null=True,
        help_text="Number of rounds issued"
    )
    duty_type = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Purpose/duty type for withdrawal"
    )
    notes = models.TextField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'transactions'
        ordering = ['-date_time']
        verbose_name = 'Transaction'
        verbose_name_plural = 'Transactions'
        indexes = [
            models.Index(fields=['-date_time']),
            models.Index(fields=['personnel', '-date_time']),
            models.Index(fields=['item', '-date_time']),
        ]
    
    def __str__(self):
        return f"{self.action} - {self.item} by {self.personnel} on {self.date_time.strftime('%d/%m/%y %H:%M')}"
    
    def is_withdrawal(self):
        """Check if transaction is a withdrawal"""
        return self.action == self.ACTION_TAKE
    
    def is_return(self):
        """Check if transaction is a return"""
        return self.action == self.ACTION_RETURN
    
    def save(self, *args, **kwargs):
        """Override save to update item status based on action with proper locking"""
        from django.db import transaction as db_transaction
        from django.db import IntegrityError
        
        is_new = self.pk is None
        
        # SECURITY FIX: Enhanced race condition protection
        if is_new:
            # Use atomic transaction with SELECT FOR UPDATE for stronger locking
            with db_transaction.atomic():
                try:
                    # Lock both personnel and item records to prevent concurrent access
                    personnel = Personnel.objects.select_for_update().get(pk=self.personnel.pk)
                    item = Item.objects.select_for_update().get(pk=self.item.pk)
                    
                    if self.action == self.ACTION_TAKE:
                        # BUSINESS RULE: Check if personnel already has an issued item
                        current_issued_count = Transaction.objects.filter(
                            personnel=personnel,
                            action=self.ACTION_TAKE,
                            item__status=Item.STATUS_ISSUED
                        ).exclude(
                            # Exclude items that have been returned
                            item__transactions__action=self.ACTION_RETURN,
                            item__transactions__date_time__gt=models.F('date_time')
                        ).count()
                        
                        if current_issued_count > 0:
                            raise ValueError(f"Personnel {personnel} already has an issued item")
                        
                        # Validate item can be taken
                        if item.status == Item.STATUS_ISSUED:
                            raise ValueError(f"Cannot take item {item.id} - already issued")
                        if item.status in [Item.STATUS_MAINTENANCE, Item.STATUS_RETIRED]:
                            raise ValueError(f"Cannot take item {item.id} - status is {item.status}")
                        
                        # Update item status atomically
                        Item.objects.filter(pk=item.pk, status=item.status).update(status=Item.STATUS_ISSUED)
                    
                    elif self.action == self.ACTION_RETURN:
                        # BUSINESS RULE: Verify this person actually has this item
                        last_take = Transaction.objects.filter(
                            item=item,
                            action=self.ACTION_TAKE,
                            personnel=personnel
                        ).order_by('-date_time').first()
                        
                        if not last_take:
                            raise ValueError(f"Personnel {personnel} cannot return item {item.id} - they never took it")
                        
                        # Check if already returned since last take
                        subsequent_return = Transaction.objects.filter(
                            item=item,
                            action=self.ACTION_RETURN,
                            date_time__gt=last_take.date_time
                        ).exists()
                        
                        if subsequent_return:
                            raise ValueError(f"Item {item.id} was already returned")
                        
                        # Validate item can be returned
                        if item.status != Item.STATUS_ISSUED:
                            raise ValueError(f"Cannot return item {item.id} - not currently issued")
                        
                        # Update item status atomically
                        Item.objects.filter(pk=item.pk, status=Item.STATUS_ISSUED).update(status=Item.STATUS_AVAILABLE)
                        
                except IntegrityError as e:
                    raise ValueError(f"Database integrity error: {str(e)}")
                
                # Save the transaction record
                super().save(*args, **kwargs)
        else:
            # For updates, just save normally
            super().save(*args, **kwargs)
        
        # Add audit logging for transaction
        try:
            from admin.models import AuditLog
            from django.contrib.auth import get_user
            from threading import local
            
            # Get current request user if available
            current_user = getattr(local(), 'user', None) if hasattr(local(), 'user') else None
            
            # Use personnel's user if no current user found
            if not current_user and self.personnel and self.personnel.user:
                current_user = self.personnel.user
            
            action_name = f'WEAPON_{self.action.upper()}'
            AuditLog.objects.create(
                performed_by=current_user,
                action='CREATE',  # Transaction is always a creation
                target_model='Transaction',
                target_id=str(self.id),
                target_name=f'{self.item.item_type} {self.item.serial}',
                description=f'{self.personnel.get_full_name()} {self.action.lower()} {self.item.item_type} {self.item.serial}',
                changes={
                    'action': self.action,
                    'item_id': self.item.id,
                    'personnel_id': self.personnel.id,
                    'item_status_change': f'{self.item.status}',
                    'timestamp': self.date_time.isoformat() if self.date_time else None
                }
            )
        except ImportError:
            pass  # AuditLog not available

