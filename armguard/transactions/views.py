"""
Transaction Views
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.contrib import messages
from .models import Transaction
from inventory.models import Item
from personnel.models import Personnel
from qr_manager.models import QRCodeImage
from django.utils import timezone


class TransactionListView(LoginRequiredMixin, ListView):
    """List all transactions with inline form for new transactions"""
    model = Transaction
    template_name = 'transactions/transaction_list.html'
    context_object_name = 'recent_transactions'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.select_related('personnel', 'item').order_by('-date_time')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get currently issued items (items with status 'Issued')
        issued_items_ids = Item.objects.filter(status='Issued').values_list('id', flat=True)
        context['issued_items'] = Transaction.objects.filter(
            item_id__in=issued_items_ids,
            action='Take'
        ).select_related('personnel', 'item').order_by('-date_time')
        return context


class TransactionDetailView(LoginRequiredMixin, DetailView):
    """View transaction details"""
    model = Transaction
    template_name = 'transactions/transaction_detail.html'
    context_object_name = 'transaction'


@login_required
def personnel_transactions(request):
    """View personnel transactions"""
    transactions = Transaction.objects.select_related('personnel', 'item').order_by('-date_time')
    context = {
        'transactions': transactions,
    }
    return render(request, 'transactions/personnel_transactions.html', context)


@login_required
def item_transactions(request):
    """View item transactions"""
    transactions = Transaction.objects.select_related('personnel', 'item').order_by('-date_time')
    context = {
        'transactions': transactions,
    }
    return render(request, 'transactions/item_transactions.html', context)


@login_required
def qr_transaction_scanner(request):
    """QR Scanner page for creating transactions"""
    return render(request, 'transactions/qr_scanner.html')


@login_required
def verify_qr_code(request):
    """API endpoint to verify scanned QR code and return details"""
    if request.method == 'POST':
        qr_data = request.POST.get('qr_data', '').strip()
        
        if not qr_data:
            return JsonResponse({'success': False, 'error': 'No QR code data provided'})
        
        try:
            # Look up QR code in database
            qr_code = QRCodeImage.objects.get(reference_id=qr_data)
            
            if qr_code.qr_type == 'personnel':
                # Get personnel details
                try:
                    personnel = Personnel.objects.get(id=qr_data)
                    return JsonResponse({
                        'success': True,
                        'type': 'personnel',
                        'id': personnel.id,
                        'name': personnel.get_full_name(),
                        'rank': personnel.rank,
                        'badge_number': personnel.badge_number,
                    })
                except Personnel.DoesNotExist:
                    return JsonResponse({'success': False, 'error': 'Personnel not found'})
                    
            elif qr_code.qr_type == 'item':
                # Get item details
                try:
                    item = Item.objects.get(id=qr_data)
                    return JsonResponse({
                        'success': True,
                        'type': 'item',
                        'id': item.id,
                        'item_type': item.item_type,
                        'serial': item.serial,
                        'status': item.status,
                        'condition': item.condition,
                    })
                except Item.DoesNotExist:
                    return JsonResponse({'success': False, 'error': 'Item not found'})
            else:
                return JsonResponse({'success': False, 'error': 'Unknown QR code type'})
                
        except QRCodeImage.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'QR code not found in system'})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


@login_required
def create_qr_transaction(request):
    """Create transaction from scanned QR codes"""
    if request.method == 'POST':
        personnel_id = request.POST.get('personnel_id')
        item_id = request.POST.get('item_id')
        action = request.POST.get('action')
        mags = request.POST.get('mags', 0)
        rounds = request.POST.get('rounds', 0)
        duty_type = request.POST.get('duty_type', '')
        notes = request.POST.get('notes', '')
        
        # Validate inputs
        if not personnel_id or not item_id or not action:
            messages.error(request, 'Missing required fields')
            return redirect('transactions:qr_scanner')
        
        try:
            personnel = Personnel.objects.get(id=personnel_id)
            item = Item.objects.get(id=item_id)
            
            # Create transaction
            transaction = Transaction.objects.create(
                personnel=personnel,
                item=item,
                action=action,
                mags=int(mags) if mags else 0,
                rounds=int(rounds) if rounds else 0,
                duty_type=duty_type,
                notes=notes,
                date_time=timezone.now()
            )
            
            messages.success(request, f'Transaction created successfully: {action} {item.item_type} - {item.serial} by {personnel.get_full_name()}')
            return redirect('transactions:qr_scanner')
            
        except Personnel.DoesNotExist:
            messages.error(request, 'Personnel not found')
        except Item.DoesNotExist:
            messages.error(request, 'Item not found')
        except Exception as e:
            messages.error(request, f'Error creating transaction: {str(e)}')
        
        return redirect('transactions:qr_scanner')
    
    return redirect('transactions:qr_scanner')


@login_required
def lookup_transactions(request):
    """Look up transactions by scanning QR code"""
    qr_data = request.GET.get('qr', '').strip()
    transactions = None
    lookup_type = None
    lookup_info = None
    
    if qr_data:
        try:
            qr_code = QRCodeImage.objects.get(reference_id=qr_data)
            
            if qr_code.qr_type == 'personnel':
                # Look up personnel transactions
                try:
                    personnel = Personnel.objects.get(id=qr_data)
                    transactions = Transaction.objects.filter(personnel=personnel).select_related('item', 'personnel').order_by('-date_time')
                    lookup_type = 'personnel'
                    lookup_info = {
                        'name': personnel.get_full_name(),
                        'rank': personnel.rank,
                        'badge_number': personnel.badge_number,
                    }
                except Personnel.DoesNotExist:
                    messages.error(request, 'Personnel not found')
                    
            elif qr_code.qr_type == 'item':
                # Look up item transactions
                try:
                    item = Item.objects.get(id=qr_data)
                    transactions = Transaction.objects.filter(item=item).select_related('item', 'personnel').order_by('-date_time')
                    lookup_type = 'item'
                    lookup_info = {
                        'item_type': item.item_type,
                        'serial': item.serial,
                        'status': item.status,
                        'condition': item.condition,
                    }
                except Item.DoesNotExist:
                    messages.error(request, 'Item not found')
            
        except QRCodeImage.DoesNotExist:
            messages.error(request, 'QR code not found in system')
    
    context = {
        'transactions': transactions,
        'lookup_type': lookup_type,
        'lookup_info': lookup_info,
        'qr_data': qr_data,
    }
    return render(request, 'transactions/lookup_transactions.html', context)


