"""
API Views for AJAX requests
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from personnel.models import Personnel
from inventory.models import Item
from transactions.models import Transaction
from qr_manager.models import QRCodeImage
from .utils import (
    parse_qr_code, 
    get_transaction_autofill_data,
    validate_transaction_action
)
import json
import logging
import os
from django.conf import settings
from print_handler.pdf_filler.form_filler import TransactionFormFiller

logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
@login_required
def get_personnel(request, personnel_id):
    """Get personnel details by ID (supports both direct ID and QR reference)"""
    result = parse_qr_code(personnel_id)
    
    if result['success'] and result['type'] == 'personnel':
        return JsonResponse(result['data'])
    elif result['success'] and result['type'] != 'personnel':
        return JsonResponse({'error': f'QR code is for {result["type"]}, not personnel'}, status=400)
    else:
        return JsonResponse({'error': result['error']}, status=404)


@require_http_methods(["GET"])
@login_required
def get_item(request, item_id):
    """Get item details by ID (supports both direct ID and QR reference)"""
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

from django.contrib import messages

@require_http_methods(["POST"])
@login_required
def create_transaction(request):
    """Create a new transaction"""
    # Validate Content-Type
    if request.content_type != 'application/json':
        return JsonResponse({'error': 'Content-Type must be application/json'}, status=415)
    
    try:
        data = json.loads(request.body)
        personnel_id = data.get('personnel_id')
        item_id = data.get('item_id')
        action = data.get('action')  # 'Take' or 'Return'
        notes = data.get('notes', '')
        mags = data.get('mags', 0)
        rounds = data.get('rounds', 0)
        duty_type = data.get('duty_type', '')
        
        # Validate required fields
        if not personnel_id or not item_id or not action:
            messages.error(request, 'Missing required fields')
            return JsonResponse({'error': 'Missing required fields'}, status=400)
        
        # Get personnel using utility function
        personnel_result = parse_qr_code(personnel_id)
        if not personnel_result['success'] or personnel_result['type'] != 'personnel':
            messages.error(request, personnel_result.get('error', 'Personnel not found'))
            return JsonResponse({'error': personnel_result.get('error', 'Personnel not found')}, status=404)
        
        personnel = Personnel.objects.get(id=personnel_result['data']['id'])
        
        # Get item using utility function
        item_result = parse_qr_code(item_id)
        if not item_result['success'] or item_result['type'] != 'item':
            messages.error(request, item_result.get('error', 'Item not found'))
            return JsonResponse({'error': item_result.get('error', 'Item not found')}, status=404)
        
        item = Item.objects.get(id=item_result['data']['id'])
        
        # Validate transaction action
        validation = validate_transaction_action(item, action)
        if not validation['valid']:
            messages.error(request, validation['message'])
            return JsonResponse({'error': validation['message']}, status=400)
        
        # Create transaction
        transaction = Transaction.objects.create(
            personnel=personnel,
            item=item,
            action=action,
            notes=notes,
            mags=mags,
            rounds=rounds,
            duty_type=duty_type,
            issued_by=request.user
        )
        
        # Item status is automatically updated by Transaction.save() method
        
        # Auto-generate and save PDF form only for withdrawals (Take)
        if action == "Take":
            try:
                form_filler = TransactionFormFiller()
                filled_pdf = form_filler.fill_transaction_form(transaction)
                
                # Save to media folder
                date_str = transaction.date_time.strftime('%Y%m%d_%H%M%S')
                filename = f"Transaction_{transaction.id}_{date_str}.pdf"
                output_path = os.path.join(settings.MEDIA_ROOT, 'transaction_forms', filename)
                
                # Ensure directory exists
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                
                with open(output_path, 'wb') as f:
                    f.write(filled_pdf.read())
                    
                logger.info(f"PDF form auto-generated for transaction {transaction.id}: {filename}")
            except Exception as e:
                logger.error(f"Failed to auto-generate PDF for transaction {transaction.id}: {str(e)}")
                # Don't fail the transaction if PDF generation fails
        
        # Add success message (PDF can be downloaded from transaction detail page)
        action_text = "withdrawn" if action == "Take" else "returned"
        messages.success(request, f'✓ Transaction #{transaction.id} completed: {item.item_type} {item.serial} {action_text} by {personnel.get_full_name()}')
        
        response_data = {
            'success': True,
            'transaction_id': transaction.id,
            'message': f'Transaction completed successfully',
            'item_new_status': item.status,  # Return updated status
            'action': action  # Return action for client-side logic
        }
        
        # Only include PDF URL for withdrawals
        if action == "Take":
            response_data['pdf_url'] = f'/print/transaction/{transaction.id}/pdf/'
        
        return JsonResponse(response_data)
        
    except json.JSONDecodeError:
        messages.error(request, 'Invalid JSON data')
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Personnel.DoesNotExist:
        messages.error(request, 'Personnel not found')
        return JsonResponse({'error': 'Personnel not found'}, status=404)
    except Item.DoesNotExist:
        messages.error(request, 'Item not found')
        return JsonResponse({'error': 'Item not found'}, status=404)
    except ValueError as e:
        logger.warning(f"Transaction validation error: {str(e)}")
        messages.error(request, str(e))
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        logger.error(f"Transaction creation failed: {str(e)}", exc_info=True)
        messages.error(request, f'Transaction failed: {str(e)}')
        return JsonResponse({'error': 'Internal server error'}, status=500)
