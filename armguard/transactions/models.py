"""
Transaction Models for ArmGuard
Based on APP/app/backend/database.py transactions table
"""
from django.db import models, transaction
from django.utils import timezone
from django.conf import settings
from django.db.models import F, Q, Exists, OuterRef
from personnel.models import Personnel
from inventory.models import Item
import logging

logger = logging.getLogger('transactions')


class Transaction(models.Model):
    """Transaction model - Records of item withdrawals and returns"""
    
    # Action choices
    ACTION_TAKE = 'Take'
    ACTION_RETURN = 'Return'
    
    ACTION_CHOICES = [
        (ACTION_TAKE, 'Take/Withdraw'),
        (ACTION_RETURN, 'Return'),
    ]

    MODE_NORMAL = 'normal'
    MODE_DEFCON = 'defcon'
    MODE_CHOICES = [
        (MODE_NORMAL, 'Normal Mode'),
        (MODE_DEFCON, 'Defcon Mode'),
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
    transaction_mode = models.CharField(max_length=20, choices=MODE_CHOICES, default=MODE_NORMAL)
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
    
    @transaction.atomic
    def save(self, *args, **kwargs):
        """Override save to update item status based on action with full atomicity"""
        is_new = self.pk is None
        
        # Validate transaction before saving
        if is_new:
            # Lock related records to prevent race conditions
            try:
                # Lock the item for update to prevent concurrent access
                locked_item = Item.objects.select_for_update().get(pk=self.item.pk)
                
                # Lock personnel record to check for existing issued items
                locked_personnel = Personnel.objects.select_for_update().get(pk=self.personnel.pk)
                
                if self.action == self.ACTION_TAKE:
                    # Check if personnel already has any issued item (atomic check)
                    active_items_query = Transaction.objects.filter(
                        personnel=self.personnel,
                        action=self.ACTION_TAKE
                    ).exclude(
                        # Exclude items that have been returned by same personnel
                        Exists(
                            Transaction.objects.filter(
                                personnel=self.personnel,
                                item=OuterRef('item'),
                                action=self.ACTION_RETURN,
                                date_time__gt=OuterRef('date_time')
                            )
                        )
                    )
                    
                    if active_items_query.exists():
                        active_item = active_items_query.first().item
                        raise ValueError(
                            f"Personnel {self.personnel} already has an active item: {active_item}"
                        )
                    
                    # Validate item availability
                    if locked_item.status != Item.STATUS_AVAILABLE:
                        if locked_item.status == Item.STATUS_ISSUED:
                            raise ValueError(
                                f"Cannot take item {locked_item.id} - already issued to another personnel"
                            )
                        elif locked_item.status in [Item.STATUS_MAINTENANCE, Item.STATUS_RETIRED]:
                            raise ValueError(
                                f"Cannot take item {locked_item.id} - status is {locked_item.status}"
                            )
                        else:
                            raise ValueError(
                                f"Cannot take item {locked_item.id} - invalid status: {locked_item.status}"
                            )
                    
                    # Update item status within the same transaction
                    locked_item.status = Item.STATUS_ISSUED
                    locked_item.save()
                    
                    logger.info(
                        f"Item {locked_item.id} issued to {self.personnel} by user {self.issued_by}"
                    )
                
                elif self.action == self.ACTION_RETURN:
                    # Validate item is currently issued
                    if locked_item.status != Item.STATUS_ISSUED:
                        raise ValueError(
                            f"Cannot return item {locked_item.id} - not currently issued (status: {locked_item.status})"
                        )
                    
                    # Verify this personnel was the one who took the item
                    last_take_transaction = Transaction.objects.filter(
                        item=locked_item,
                        action=self.ACTION_TAKE
                    ).exclude(
                        Exists(
                            Transaction.objects.filter(
                                item=locked_item,
                                action=self.ACTION_RETURN,
                                date_time__gt=OuterRef('date_time')
                            )
                        )
                    ).first()
                    
                    if not last_take_transaction or last_take_transaction.personnel != self.personnel:
                        current_holder = last_take_transaction.personnel if last_take_transaction else "Unknown"
                        raise ValueError(
                            f"Cannot return item {locked_item.id} - was issued to {current_holder}, not {self.personnel}"
                        )
                    
                    # Update item status within the same transaction
                    locked_item.status = Item.STATUS_AVAILABLE
                    locked_item.save()
                    
                    logger.info(
                        f"Item {locked_item.id} returned by {self.personnel} via user {self.issued_by}"
                    )
                
            except Item.DoesNotExist:
                raise ValueError(f"Item {self.item.pk} does not exist")
            except Personnel.DoesNotExist:
                raise ValueError(f"Personnel {self.personnel.pk} does not exist")
            except Exception as e:
                logger.error(f"Transaction validation failed: {e}")
                raise
        
        # Save the transaction record
        super().save(*args, **kwargs)
        
        logger.info(
            f"Transaction {self.id} created: {self.action} {self.item} by {self.personnel}"
        )

