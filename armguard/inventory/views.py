"""
Inventory Views
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Item


class ItemListView(LoginRequiredMixin, ListView):
    """List all items"""
    model = Item
    template_name = 'inventory/item_list.html'
    context_object_name = 'items'
    paginate_by = 100

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.order_by('item_type', 'serial')
    
    def get_context_data(self, **kwargs):
        """Add QR code objects to items"""
        context = super().get_context_data(**kwargs)
        # Import here to avoid circular imports
        from qr_manager.models import QRCodeImage
        
        # Attach QR code object to each item
        for item in context['items']:
            try:
                item.qr_code_obj = QRCodeImage.objects.get(
                    qr_type=QRCodeImage.TYPE_ITEM,
                    reference_id=item.id  # Use item.id, not item.serial
                )
            except QRCodeImage.DoesNotExist:
                item.qr_code_obj = None
        
        return context


class ItemDetailView(LoginRequiredMixin, DetailView):
    """View item details"""
    model = Item
    template_name = 'inventory/item_detail.html'
    context_object_name = 'item'
    
    def get_context_data(self, **kwargs):
        """Add QR code object to context"""
        context = super().get_context_data(**kwargs)
        # Import here to avoid circular imports
        from qr_manager.models import QRCodeImage
        try:
            context['qr_code_obj'] = QRCodeImage.objects.get(
                qr_type=QRCodeImage.TYPE_ITEM,
                reference_id=self.object.id  # Use item.id, not item.serial
            )
        except QRCodeImage.DoesNotExist:
            context['qr_code_obj'] = None
        return context


@login_required
def update_item_status(request, pk):
    """Update item status (only for non-issued items)"""
    if request.method != 'POST':
        return redirect('inventory:item_detail', pk=pk)
    
    item = get_object_or_404(Item, pk=pk)
    new_status = request.POST.get('status')
    
    # Only allow status changes if item is not issued
    if item.status == Item.STATUS_ISSUED:
        messages.error(request, 'Cannot change status of issued items. Please return the item first.')
        return redirect('inventory:item_detail', pk=pk)
    
    # Validate new status
    valid_statuses = [Item.STATUS_AVAILABLE, Item.STATUS_MAINTENANCE, Item.STATUS_RETIRED]
    if new_status not in valid_statuses:
        messages.error(request, 'Invalid status selected.')
        return redirect('inventory:item_detail', pk=pk)
    
    # Update status
    old_status = item.status
    item.status = new_status
    item.save()
    
    messages.success(request, f'Item status changed from "{old_status}" to "{new_status}".')
    return redirect('inventory:item_detail', pk=pk)

