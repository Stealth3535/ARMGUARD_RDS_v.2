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
            return JsonResponse({'error': 'Missing required fields'}, status=400)
        
        # Get personnel using utility function
        personnel_result = parse_qr_code(personnel_id)
        if not personnel_result['success'] or personnel_result['type'] != 'personnel':
            return JsonResponse({'error': personnel_result.get('error', 'Personnel not found')}, status=404)
        
        personnel = Personnel.objects.get(id=personnel_result['data']['id'])
        
        # Get item using utility function
        item_result = parse_qr_code(item_id)
        if not item_result['success'] or item_result['type'] != 'item':
            return JsonResponse({'error': item_result.get('error', 'Item not found')}, status=404)
        
        item = Item.objects.get(id=item_result['data']['id'])
        
        # Validate transaction action
        validation = validate_transaction_action(item, action)
        if not validation['valid']:
            return JsonResponse({'error': validation['message']}, status=400)
        
        # Create transaction
        transaction = Transaction.objects.create(
            personnel=personnel,
            item=item,
            action=action,
            notes=notes,
            mags=mags,
            rounds=rounds,
            duty_type=duty_type
        )
        
        # Item status is automatically updated by Transaction.save() method
        
        return JsonResponse({
            'success': True,
            'transaction_id': transaction.id,
            'message': f'Transaction completed successfully',
            'item_new_status': item.status  # Return updated status
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Personnel.DoesNotExist:
        return JsonResponse({'error': 'Personnel not found'}, status=404)
    except Item.DoesNotExist:
        return JsonResponse({'error': 'Item not found'}, status=404)
    except ValueError as e:
        logger.warning(f"Transaction validation error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        logger.error(f"Transaction creation failed: {str(e)}", exc_info=True)
        return JsonResponse({'error': 'Internal server error'}, status=500)
