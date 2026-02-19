"""
API Views for AJAX requests - Enhanced with Atomic Transactions and Audit Context
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Exists, OuterRef
from personnel.models import Personnel
from inventory.models import Item
from transactions.models import Transaction
from qr_manager.models import QRCodeImage
from .utils import (
    parse_qr_code, 
    get_transaction_autofill_data,
    validate_transaction_action
)
from .api_forms import TransactionCreateForm, PersonnelLookupForm, ItemLookupForm
from .rate_limiting import api_rate_limit
from .middleware.audit_middleware import TransactionAuditContext, audit_operation
import json
import logging
import os
from django.conf import settings
from print_handler.pdf_filler.form_filler import TransactionFormFiller

logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
@login_required
@api_rate_limit
def get_personnel(request, personnel_id):
    """Get personnel details by ID (supports both direct ID and QR reference)"""
    # Validate input using form
    form = PersonnelLookupForm({'personnel_id': personnel_id})
    if not form.is_valid():
        return JsonResponse({'error': 'Invalid personnel ID format'}, status=400)
    
    result = parse_qr_code(personnel_id)
    
    if result['success'] and result['type'] == 'personnel':
        resolved_personnel_id = result['data'].get('id')

        active_items_query = Transaction.objects.filter(
            personnel_id=resolved_personnel_id,
            action=Transaction.ACTION_TAKE
        ).exclude(
            Exists(
                Transaction.objects.filter(
                    personnel_id=resolved_personnel_id,
                    item=OuterRef('item'),
                    action=Transaction.ACTION_RETURN,
                    date_time__gt=OuterRef('date_time')
                )
            )
        )

        has_issued_firearm = active_items_query.exists()
        result['data']['has_issued_firearm'] = has_issued_firearm

        if has_issued_firearm:
            active_item_tx = active_items_query.select_related('item').first()
            if active_item_tx and active_item_tx.item:
                result['data']['issued_item_id'] = active_item_tx.item.id
                result['data']['issued_item_serial'] = active_item_tx.item.serial
                result['data']['issued_item_type'] = active_item_tx.item.item_type

        return JsonResponse(result['data'])
    elif result['success'] and result['type'] != 'personnel':
        return JsonResponse({'error': f'QR code is for {result["type"]}, not personnel'}, status=400)
    else:
        return JsonResponse({'error': result['error']}, status=404)


@require_http_methods(["GET"])
@login_required
@api_rate_limit
def get_item(request, item_id):
    """Get item details by ID (supports both direct ID and QR reference)"""
    # Validate input using form
    form = ItemLookupForm({'item_id': item_id})
    if not form.is_valid():
        return JsonResponse({'error': 'Invalid item ID format'}, status=400)
    
    result = parse_qr_code(item_id)
    
    if result['success'] and result['type'] == 'item':
        # Add autofill suggestion if duty_type is provided
        duty_type = request.GET.get('duty_type', '')
        if duty_type:
            autofill = get_transaction_autofill_data(result['data']['item_type'], duty_type)
            result['data']['autofill'] = autofill
        
        return JsonResponse(result['data'])
    elif result['success'] and result['type'] != 'item':
        return JsonResponse({'error': f'QR code is for {result["type"]}, not item'}, status=400)
    else:
        return JsonResponse({'error': result['error']}, status=404)

@require_http_methods(["POST"])
@login_required
@audit_operation('CREATE_TRANSACTION')
def create_transaction(request):
    """Create a new transaction with full atomicity and comprehensive audit logging"""
    # Validate Content-Type
    if request.content_type != 'application/json':
        return JsonResponse({'error': 'Content-Type must be application/json'}, status=415)
    
    try:
        data = json.loads(request.body)
        personnel_id = data.get('personnel_id')
        item_id = data.get('item_id')
        action = data.get('action')  # 'Take' or 'Return'
        mode = str(data.get('mode', 'normal')).strip().lower()
        notes = data.get('notes', '')
        mags = data.get('mags', 0)
        rounds = data.get('rounds', 0)
        duty_type = data.get('duty_type', '')
        
        # Enhanced validation
        if not personnel_id or not item_id or not action:
            messages.error(request, 'Missing required fields')
            return JsonResponse({'error': 'Missing required fields'}, status=400)
        
        if action not in ['Take', 'Return']:
            messages.error(request, 'Invalid action type')
            return JsonResponse({'error': 'Action must be "Take" or "Return"'}, status=400)

        if mode not in ['normal', 'defcon']:
            messages.error(request, 'Invalid transaction mode')
            return JsonResponse({'error': 'Mode must be "normal" or "defcon"'}, status=400)

        if mode == 'defcon' and action != 'Take':
            messages.error(request, 'Defcon mode allows Withdraw transactions only')
            return JsonResponse({'error': 'Defcon mode allows Withdraw transactions only'}, status=400)
        
        # Use atomic transaction with audit context
        with transaction.atomic():
            with TransactionAuditContext(
                request, 
                f'{action.upper()}_ITEM',
                {'personnel_id': personnel_id, 'item_id': item_id}
            ) as audit_ctx:
                
                # Get personnel using utility function
                personnel_result = parse_qr_code(personnel_id)
                if not personnel_result['success'] or personnel_result['type'] != 'personnel':
                    error_msg = personnel_result.get('error', 'Personnel not found')
                    messages.error(request, error_msg)
                    logger.warning(f"Personnel lookup failed: {error_msg}")
                    return JsonResponse({'error': error_msg}, status=404)
                
                try: 
                    personnel = Personnel.objects.select_for_update().get(id=personnel_result['data']['id'])
                    if personnel.status != Personnel.STATUS_ACTIVE:
                        error_msg = f'Personnel {personnel_id} is not active (status: {personnel.status})'
                        messages.error(request, error_msg)
                        return JsonResponse({'error': error_msg}, status=400)
                except Personnel.DoesNotExist:
                    error_msg = 'Personnel not found'
                    messages.error(request, error_msg)
                    return JsonResponse({'error': error_msg}, status=404)
                
                # Get item using utility function
                item_result = parse_qr_code(item_id)
                if not item_result['success'] or item_result['type'] != 'item':
                    error_msg = item_result.get('error', 'Item not found')
                    messages.error(request, error_msg)
                    logger.warning(f"Item lookup failed: {error_msg}")
                    return JsonResponse({'error': error_msg}, status=404)
                
                try:
                    item = Item.objects.select_for_update().get(id=item_result['data']['id'])
                except Item.DoesNotExist:
                    error_msg = 'Item not found'
                    messages.error(request, error_msg)
                    return JsonResponse({'error': error_msg}, status=404)
                
                # Validate transaction action (but let the model handle detailed business logic)
                validation = validate_transaction_action(item, action)
                if not validation['valid']:
                    error_msg = validation['message']
                    messages.error(request, error_msg)
                    logger.warning(f"Transaction validation failed: {error_msg}")
                    return JsonResponse({'error': error_msg}, status=400)
                
                # Set audit context for the transaction
                transaction_data = {
                    'personnel': personnel,
                    'item': item,
                    'action': action,
                    'transaction_mode': mode,
                    'notes': notes,
                    'mags': mags,
                    'rounds': rounds,
                    'duty_type': duty_type,
                    'issued_by': request.user
                }
                
                # Create transaction - model's atomic save() handles all validation and status updates
                try:
                    transaction_obj = Transaction.objects.create(**transaction_data)
                    logger.info(f"Transaction {transaction_obj.id} created: {action} {item_id} by {personnel_id}")
                    
                except ValueError as ve:
                    # Business rule violation (from model validation)
                    error_msg = str(ve)
                    messages.error(request, error_msg)
                    logger.warning(f"Business rule violation: {error_msg}")
                    return JsonResponse({'error': error_msg}, status=400)
                
                except Exception as e:
                    # Unexpected error
                    logger.error(f"Transaction creation failed: {e}", exc_info=True)
                    messages.error(request, 'Transaction creation failed')
                    return JsonResponse({'error': 'Internal server error'}, status=500)
                
                # Auto-generate PDF form only for withdrawals (Take)
                pdf_url = None
                if action == "Take":
                    try:
                        form_filler = TransactionFormFiller()
                        filled_pdf = form_filler.fill_transaction_form(transaction_obj)
                        
                        # Save to media folder
                        date_str = transaction_obj.date_time.strftime('%Y%m%d_%H%M%S')
                        filename = f"Transaction_{transaction_obj.id}_{date_str}.pdf"
                        output_path = os.path.join(settings.MEDIA_ROOT, 'transaction_forms', filename)
                        
                        # Ensure directory exists
                        os.makedirs(os.path.dirname(output_path), exist_ok=True)
                        
                        with open(output_path, 'wb') as f:
                            f.write(filled_pdf.read())
                        
                        pdf_url = f'/print/transaction/{transaction_obj.id}/pdf/'
                        logger.info(f"PDF form auto-generated for transaction {transaction_obj.id}: {filename}")
                        
                    except Exception as e:
                        logger.error(f"Failed to auto-generate PDF for transaction {transaction_obj.id}: {str(e)}")
                        # Don't fail the transaction if PDF generation fails
                        pdf_url = None
                
                # Success message
                action_text = "withdrawn" if action == "Take" else "returned"
                success_msg = f'✓ Transaction #{transaction_obj.id} completed: {item.item_type} {item.serial} {action_text} by {personnel.get_full_name()}'
                messages.success(request, success_msg)
                
                # Comprehensive response data with validated transaction_id
                response_data = {
                    'success': True,
                    'transaction_id': int(transaction_obj.id),  # Ensure it's an integer
                    'message': 'Transaction completed successfully',
                    'transaction': {
                        'id': int(transaction_obj.id),  # Ensure it's an integer
                        'personnel': {
                            'id': personnel.id,
                            'name': personnel.get_full_name(),
                            'rank': personnel.rank or 'N/A'
                        },
                        'item': {
                            'id': item.id,
                            'type': item.item_type,
                            'serial': item.serial,
                            'status': item.status  # Updated status
                        },
                        'action': action,
                        'datetime': transaction_obj.date_time.isoformat(),
                        'issued_by': request.user.username
                    },
                    'item_new_status': item.status,
                    'action': action
                }
                
                # Add PDF URL for Take transactions (ensure transaction_id is valid)
                if pdf_url and transaction_obj.id:
                    response_data['pdf_url'] = pdf_url
                    logger.info(f"Response includes PDF URL: {pdf_url} for transaction {transaction_obj.id}")
                
                # Log response for debugging
                logger.info(f"Transaction response data: transaction_id={response_data['transaction_id']}, action={action}")
                
                return JsonResponse(response_data)
        
    except json.JSONDecodeError:
        messages.error(request, 'Invalid JSON data')
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Unexpected error in create_transaction: {e}", exc_info=True)
        messages.error(request, 'Internal server error')
        return JsonResponse({'error': 'Internal server error'}, status=500)
