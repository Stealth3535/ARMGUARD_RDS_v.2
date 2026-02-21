"""
Inventory Views
"""
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Item
from core.network_decorators import lan_required, read_only_on_wan
from core.notifications import broadcast_inventory_update


class ItemListView(LoginRequiredMixin, ListView):
    """List all items - Read-only on WAN, full access on LAN"""
    model = Item
    template_name = 'inventory/item_list.html'
    context_object_name = 'items'
    paginate_by = 100

    @read_only_on_wan
    def dispatch(self, request, *args, **kwargs):
        """Override dispatch to apply network restrictions"""
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.order_by('item_type', 'serial')
    
    def get_context_data(self, **kwargs):
        """Add QR code objects to items"""
        context = super().get_context_data(**kwargs)
        # Import here to avoid circular imports
        from qr_manager.models import QRCodeImage
        from admin.permissions import check_restricted_admin
        
        # Attach QR code object to each item
        for item in context['items']:
            try:
                item.qr_code_obj = QRCodeImage.objects.get(
                    qr_type=QRCodeImage.TYPE_ITEM,
                    reference_id=item.id  # Use item.id, not item.serial
                )
            except QRCodeImage.DoesNotExist:
                item.qr_code_obj = None
        
        # Check if user is unrestricted admin (not restricted admin or armorer)
        is_admin = self.request.user.is_superuser or self.request.user.groups.filter(name='Admin').exists()
        is_restricted = check_restricted_admin(self.request.user)
        context['is_admin'] = is_admin and not is_restricted
        
        return context


class ItemDetailView(LoginRequiredMixin, DetailView):
    """View item details - Read-only on WAN, full access on LAN"""
    model = Item
    template_name = 'inventory/item_detail.html'
    context_object_name = 'item'
    
    @read_only_on_wan
    def dispatch(self, request, *args, **kwargs):
        """Override dispatch to apply network restrictions"""
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        """Add QR code object and last take transaction to context"""
        context = super().get_context_data(**kwargs)
        # Import here to avoid circular imports
        from qr_manager.models import QRCodeImage
        from transactions.models import Transaction
        from admin.permissions import check_restricted_admin

        qr_code_obj = None
        try:
            qr_code_obj = QRCodeImage.objects.get(
                qr_type=QRCodeImage.TYPE_ITEM,
                reference_id=self.object.id
            )
            # Auto-heal: regenerate if file is missing OR filename stem has dots
            needs_regen = False
            if not qr_code_obj.qr_image:
                needs_regen = True
            else:
                stem = os.path.splitext(os.path.basename(qr_code_obj.qr_image.name))[0]
                full_path = os.path.join(settings.MEDIA_ROOT, qr_code_obj.qr_image.name)
                if '.' in stem or not os.path.exists(full_path):
                    needs_regen = True
            if needs_regen:
                try:
                    if qr_code_obj.qr_image:
                        qr_code_obj.qr_image.delete(save=False)
                    qr_code_obj.qr_image = None
                    qr_code_obj.generate_qr_code()
                    qr_code_obj.save()
                    logger.info('Auto-healed QR for %s → %s',
                                self.object.id, qr_code_obj.qr_image.name)
                except Exception as e:
                    logger.error('Failed to auto-heal QR for %s: %s',
                                 self.object.id, e)
        except QRCodeImage.DoesNotExist:
            # No active record — find inactive or create fresh
            try:
                qr_code_obj, created = QRCodeImage.all_objects.get_or_create(
                    qr_type=QRCodeImage.TYPE_ITEM,
                    reference_id=self.object.id,
                    defaults={'qr_data': self.object.id, 'is_active': True},
                )
                if not qr_code_obj.is_active:
                    qr_code_obj.is_active = True
                    qr_code_obj.deleted_at = None
                # Check file exists
                file_missing = (
                    not qr_code_obj.qr_image or
                    not os.path.exists(
                        os.path.join(settings.MEDIA_ROOT, qr_code_obj.qr_image.name)
                    )
                )
                if file_missing:
                    if qr_code_obj.qr_image:
                        qr_code_obj.qr_image.delete(save=False)
                    qr_code_obj.qr_image = None
                    qr_code_obj.generate_qr_code()
                qr_code_obj.save()
                logger.info('Auto-created/healed QR for %s', self.object.id)
            except Exception as e:
                logger.error('Failed to auto-create/heal QR for %s: %s', self.object.id, e)
                qr_code_obj = None

        context['qr_code_obj'] = qr_code_obj
        
        # Get last 'Take' transaction for issued items
        if self.object.status == 'Issued':
            last_take = self.object.transactions.filter(action='Take').order_by('-date_time').first()
            # Check if there's no return after this take
            if last_take and not self.object.transactions.filter(action='Return', date_time__gt=last_take.date_time).exists():
                context['last_take'] = last_take
            else:
                context['last_take'] = None
        else:
            context['last_take'] = None
        
        # Check if user is unrestricted admin (not restricted admin or armorer)
        is_admin = self.request.user.is_superuser or self.request.user.groups.filter(name='Admin').exists()
        is_restricted = check_restricted_admin(self.request.user)
        context['is_admin'] = is_admin and not is_restricted
            
        return context


def is_admin_or_armorer(user):
    """Check if user is admin, superuser, or armorer - can modify items"""
    return user.is_authenticated and (
        user.is_superuser or 
        user.groups.filter(name='Admin').exists() or 
        user.groups.filter(name='Armorer').exists()
    )


from django.contrib.auth.decorators import user_passes_test
import logging
import os

logger = logging.getLogger(__name__)


@login_required
@user_passes_test(is_admin_or_armorer, login_url='/')
def update_item_status(request, pk):
    """Update item status (only for non-issued items) - Admin/Armorer only"""
    if request.method != 'POST':
        return redirect('inventory:item_detail', pk=pk)
    
    item = get_object_or_404(Item, pk=pk)
    new_status = request.POST.get('status', '').strip()
    
    # Input validation
    if not new_status:
        messages.error(request, 'Status is required.')
        return redirect('inventory:item_detail', pk=pk)
    
    # Only allow status changes if item is not issued
    if item.status == Item.STATUS_ISSUED:
        messages.error(request, 'Cannot change status of issued items. Please return the item first.')
        return redirect('inventory:item_detail', pk=pk)
    
    # Validate new status
    valid_statuses = [Item.STATUS_AVAILABLE, Item.STATUS_MAINTENANCE, Item.STATUS_RETIRED]
    if new_status not in valid_statuses:
        logger.warning("Invalid status attempted: %s by user %s", new_status, request.user.username)
        messages.error(request, 'Invalid status selected.')
        return redirect('inventory:item_detail', pk=pk)
    
    # Update status
    old_status = item.status
    item.status = new_status
    item.save()
    
    # Broadcast real-time inventory update
    broadcast_inventory_update(item, previous_status=old_status)
    
    logger.info("Item %s status changed from %s to %s by %s", pk, old_status, new_status, request.user.username)
    messages.success(request, f'Item status changed from "{old_status}" to "{new_status}".')
    return redirect('inventory:item_detail', pk=pk)

