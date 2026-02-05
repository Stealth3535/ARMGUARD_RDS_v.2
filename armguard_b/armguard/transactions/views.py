"""
Transaction Views
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q
from django.http import JsonResponse
from django.contrib import messages
from .models import Transaction
from inventory.models import Item
from personnel.models import Personnel
from qr_manager.models import QRCodeImage
from django.utils import timezone
from core.network_decorators import lan_required, read_only_on_wan, network_aware_permission_required


def is_admin_or_armorer(user):
    """Check if user is admin, superuser, or armorer - can issue items"""
    return user.is_authenticated and (
        user.is_superuser or 
        user.groups.filter(name='Admin').exists() or 
        user.groups.filter(name='Armorer').exists()
    )


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
@lan_required  # NEW: Transaction creation requires LAN access for security
@user_passes_test(is_admin_or_armorer)
def qr_transaction_scanner(request):
    """QR Scanner page for creating transactions - Admin and Armorer only"""
    return render(request, 'transactions/qr_scanner.html')


@login_required
def verify_qr_code(request):
    """API endpoint to verify scanned QR code and return details - SECURITY ENHANCED"""
    if request.method == 'POST':
        qr_data = request.POST.get('qr_data', '').strip()
        
        if not qr_data:
            return JsonResponse({'success': False, 'error': 'No QR code data provided'})
        
        # SECURITY FIX: Input validation to prevent injection attacks
        import re
        if not re.match(r'^[A-Za-z0-9_:-]{1,100}$', qr_data):
            return JsonResponse({
                'success': False, 
                'error': 'Invalid QR code format - contains illegal characters'
            })
        
        # Parse QR code data with enhanced validation
        # Format: "PERSONNEL:PE-123456:SGT Name:123456" or "ITEM:ITM-123456:Type:Serial"
        personnel_id = None
        item_id = None
        
        try:
            if qr_data.startswith('PERSONNEL:'):
                # Extract personnel ID from QR data
                parts = qr_data.split(':')
                if len(parts) >= 2:
                    personnel_id = parts[1]
            elif qr_data.startswith('ITEM:'):
                # Extract item ID from QR data
                parts = qr_data.split(':')
                if len(parts) >= 2:
                    item_id = parts[1]
            else:
                # Assume it's a direct ID (legacy format)
                # Try to determine type by prefix
                if qr_data.startswith('PE-') or qr_data.startswith('PO-'):
                    personnel_id = qr_data
                elif qr_data.startswith('ITM-'):
                    item_id = qr_data
                else:
                    return JsonResponse({'success': False, 'error': 'Invalid QR code format'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': f'Error parsing QR code: {str(e)}'})
        
        try:
            if personnel_id:
                # Look up QR code and validate
                qr_code = QRCodeImage.objects.get(qr_type='personnel', reference_id=personnel_id)
                
                # Validate QR code is active
                is_valid, message = qr_code.is_valid_for_transaction()
                if not is_valid:
                    return JsonResponse({'success': False, 'error': message})
                
                # Get personnel details
                try:
                    personnel = Personnel.objects.get(id=personnel_id)
                    badge_number = ''
                    if personnel.user and hasattr(personnel.user, 'userprofile'):
                        badge_number = personnel.user.userprofile.badge_number or ''
                    return JsonResponse({
                        'success': True,
                        'type': 'personnel',
                        'id': personnel.id,
                        'name': personnel.get_full_name(),
                        'rank': personnel.rank,
                        'badge_number': badge_number,
                        'serial': personnel.serial,
                        'group': personnel.group,
                    })
                except Personnel.DoesNotExist:
                    return JsonResponse({'success': False, 'error': 'Personnel not found'})
                    
            elif item_id:
                # Look up QR code and validate
                qr_code = QRCodeImage.objects.get(qr_type='item', reference_id=item_id)
                
                # Validate QR code is active
                is_valid, message = qr_code.is_valid_for_transaction()
                if not is_valid:
                    return JsonResponse({'success': False, 'error': message})
                
                # Get item details
                try:
                    item = Item.objects.get(id=item_id)
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
                return JsonResponse({'success': False, 'error': 'Could not parse QR code data'})
                
        except QRCodeImage.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'QR code not found in system'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': f'Error processing QR code: {str(e)}'})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


@login_required
@lan_required  # NEW: Transaction creation requires LAN access for security
@user_passes_test(is_admin_or_armorer)
def create_qr_transaction(request):
    """Create transaction from scanned QR codes - Admin and Armorer only"""
    import logging
    logger = logging.getLogger(__name__)
    
    if request.method == 'POST':
        # MEDIUM-3: Enhanced input validation
        personnel_id = request.POST.get('personnel_id', '').strip()
        item_id = request.POST.get('item_id', '').strip()
        action = request.POST.get('action', '').strip()
        duty_type = request.POST.get('duty_type', '').strip()
        notes = request.POST.get('notes', '').strip()
        
        # Validate required fields
        if not personnel_id or not item_id or not action:
            messages.error(request, 'Missing required fields: personnel_id, item_id, and action are required')
            return redirect('transactions:qr_scanner')
        
        # Validate action is one of allowed values
        allowed_actions = ['Take', 'Return']
        if action not in allowed_actions:
            logger.warning("Invalid action attempted: %s by user %s", action, request.user.username)
            messages.error(request, f'Invalid action. Must be one of: {", ".join(allowed_actions)}')
            return redirect('transactions:qr_scanner')
        
        # Validate and sanitize numeric inputs
        try:
            mags_raw = request.POST.get('mags', '0').strip()
            rounds_raw = request.POST.get('rounds', '0').strip()
            mags = int(mags_raw) if mags_raw else 0
            rounds = int(rounds_raw) if rounds_raw else 0
            
            # Validate non-negative values
            if mags < 0 or rounds < 0:
                messages.error(request, 'Magazines and rounds must be non-negative numbers')
                return redirect('transactions:qr_scanner')
            
            # Validate reasonable limits
            if mags > 100 or rounds > 10000:
                logger.warning("Unusually high values: mags=%d, rounds=%d by user %s", mags, rounds, request.user.username)
                messages.error(request, 'Invalid quantity: values exceed reasonable limits')
                return redirect('transactions:qr_scanner')
                
        except (ValueError, TypeError) as e:
            logger.warning("Invalid numeric input for transaction: %s", str(e))
            messages.error(request, 'Invalid input: magazines and rounds must be valid numbers')
            return redirect('transactions:qr_scanner')
        
        # Sanitize text inputs (limit length to prevent DoS)
        duty_type = duty_type[:100] if duty_type else ''
        notes = notes[:500] if notes else ''
        
        try:
            personnel = Personnel.objects.get(id=personnel_id)
            item = Item.objects.get(id=item_id)
            
            # Create transaction
            transaction = Transaction.objects.create(
                personnel=personnel,
                item=item,
                action=action,
                mags=mags,
                rounds=rounds,
                duty_type=duty_type,
                notes=notes,
                date_time=timezone.now(),
                issued_by=request.user
            )
            
            logger.info("Transaction #%d created by %s: %s %s", transaction.id, request.user.username, action, item_id)
            messages.success(request, f'✓ Transaction #{transaction.id} created: {action} {item.item_type} - {item.serial} by {personnel.get_full_name()}')
            return redirect('transactions:qr_scanner')
            
        except Personnel.DoesNotExist:
            logger.warning("Personnel not found: %s", personnel_id)
            messages.error(request, 'Personnel not found')
        except Item.DoesNotExist:
            logger.warning("Item not found: %s", item_id)
            messages.error(request, 'Item not found')
        except ValueError as e:
            # Transaction validation errors (e.g., item already issued)
            logger.warning("Transaction validation failed: %s", str(e))
            messages.error(request, str(e))
        except Exception as e:
            logger.error("Unexpected error creating transaction: %s", str(e), exc_info=True)
            messages.error(request, 'An error occurred while creating the transaction')
        
        return redirect('transactions:qr_scanner')
    
    return redirect('transactions:qr_scanner')


@login_required
def lookup_transactions(request):
    """Look up transactions by scanning QR code"""
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    
    qr_data = request.GET.get('qr', '').strip()
    transactions = None
    lookup_type = None
    lookup_info = None
    page_obj = None
    
    if qr_data:
        # Parse QR code data
        personnel_id = None
        item_id = None
        
        if qr_data.startswith('PERSONNEL:'):
            parts = qr_data.split(':')
            if len(parts) >= 2:
                personnel_id = parts[1]
        elif qr_data.startswith('ITEM:'):
            parts = qr_data.split(':')
            if len(parts) >= 2:
                item_id = parts[1]
        else:
            # Legacy format - direct ID
            if qr_data.startswith('PE-') or qr_data.startswith('PO-'):
                personnel_id = qr_data
            elif qr_data.startswith('ITM-'):
                item_id = qr_data
        
        try:
            if personnel_id:
                qr_code = QRCodeImage.objects.get(qr_type='personnel', reference_id=personnel_id)
                
                # Validate QR code is active
                is_valid, message = qr_code.is_valid_for_transaction()
                if not is_valid:
                    messages.error(request, f"Cannot lookup: {message}")
                    return render(request, 'transactions/lookup_transactions.html', {})
                
                # Look up personnel transactions
                try:
                    personnel = Personnel.objects.get(id=personnel_id)
                    transaction_list = Transaction.objects.filter(personnel=personnel).select_related('item', 'personnel').order_by('-date_time')
                    lookup_type = 'personnel'
                    badge_number = ''
                    if personnel.user and hasattr(personnel.user, 'userprofile'):
                        badge_number = personnel.user.userprofile.badge_number or ''
                    lookup_info = {
                        'name': personnel.get_full_name(),
                        'rank': personnel.rank,
                        'badge_number': badge_number,
                        'serial': personnel.serial,
                        'group': personnel.group,
                    }
                    
                    # Paginate results
                    paginator = Paginator(transaction_list, 20)
                    page = request.GET.get('page', 1)
                    try:
                        page_obj = paginator.page(page)
                        transactions = page_obj.object_list
                    except (EmptyPage, PageNotAnInteger):
                        page_obj = paginator.page(1)
                        transactions = page_obj.object_list
                        
                except Personnel.DoesNotExist:
                    messages.error(request, 'Personnel not found')
                except Exception as e:
                    messages.error(request, f'Error looking up personnel: {str(e)}')
                    
            elif item_id:
                qr_code = QRCodeImage.objects.get(qr_type='item', reference_id=item_id)
                
                # Validate QR code is active
                is_valid, message = qr_code.is_valid_for_transaction()
                if not is_valid:
                    messages.error(request, f"Cannot lookup: {message}")
                    return render(request, 'transactions/lookup_transactions.html', {})
                
                # Look up item transactions
                try:
                    item = Item.objects.get(id=item_id)
                    transaction_list = Transaction.objects.filter(item=item).select_related('item', 'personnel').order_by('-date_time')
                    lookup_type = 'item'
                    lookup_info = {
                        'item_type': item.item_type,
                        'serial': item.serial,
                        'status': item.status,
                        'condition': item.condition,
                    }
                    
                    # Paginate results
                    paginator = Paginator(transaction_list, 20)
                    page = request.GET.get('page', 1)
                    try:
                        page_obj = paginator.page(page)
                        transactions = page_obj.object_list
                    except (EmptyPage, PageNotAnInteger):
                        page_obj = paginator.page(1)
                        transactions = page_obj.object_list
                        
                except Item.DoesNotExist:
                    messages.error(request, 'Item not found')
                except Exception as e:
                    messages.error(request, f'Error looking up item: {str(e)}')
            
        except QRCodeImage.DoesNotExist:
            messages.error(request, 'QR code not found in system')
    
    context = {
        'transactions': transactions,
        'lookup_type': lookup_type,
        'lookup_info': lookup_info,
        'qr_data': qr_data,
        'page_obj': page_obj,
    }
    return render(request, 'transactions/lookup_transactions.html', context)


