"""
Transaction Models for ArmGuard
Based on APP/app/backend/database.py transactions table
"""
from django.db import models
from django.utils import timezone
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
        """Override save to update item status based on action"""
        is_new = self.pk is None
        
        # Validate transaction before saving
        if is_new:
            if self.action == self.ACTION_TAKE:
                # Item cannot be taken — personnel already has an issued item
                current_issued_items = Item.objects.filter(status=Item.STATUS_ISSUED)
                for item in current_issued_items:
                    # Check if this item was last taken by this personnel
                    last_transaction = item.transactions.order_by('-date_time').first()
                    if (last_transaction and 
                        last_transaction.action == self.ACTION_TAKE and 
                        last_transaction.personnel == self.personnel):
                        raise ValueError(f"Item cannot be taken — personnel {self.personnel} already has an issued item: {item}")
                
                # Cannot take item that's already issued
                if self.item.status == Item.STATUS_ISSUED:
                    raise ValueError(f"Cannot take item {self.item.id} - already issued")
                # Cannot take item in maintenance or retired
                if self.item.status in [Item.STATUS_MAINTENANCE, Item.STATUS_RETIRED]:
                    raise ValueError(f"Cannot take item {self.item.id} - status is {self.item.status}")
            
            elif self.action == self.ACTION_RETURN:
                # Cannot return item that's not issued
                if self.item.status != Item.STATUS_ISSUED:
                    raise ValueError(f"Cannot return item {self.item.id} - not currently issued")
        
        super().save(*args, **kwargs)
        
        # Update item status after saving transaction
        if is_new:
            if self.action == self.ACTION_TAKE:
                self.item.status = Item.STATUS_ISSUED
                self.item.save()
            elif self.action == self.ACTION_RETURN:
                self.item.status = Item.STATUS_AVAILABLE
                self.item.save()

