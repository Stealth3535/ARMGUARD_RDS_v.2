"""
Utility functions for ArmGuard
"""
from qr_manager.models import QRCodeImage
from personnel.models import Personnel
from inventory.models import Item
from django.core.exceptions import ObjectDoesNotExist


def parse_qr_code(qr_data):
    """
    Parse QR code data and determine what type of entity it represents.
    Returns a dictionary with entity type and details.
    
    Args:
        qr_data (str): The scanned QR code data
        
    Returns:
        dict: {
            'success': bool,
            'type': 'personnel' | 'item' | None,
            'data': dict with entity details,
            'error': str (if success is False)
        }
    """
    if not qr_data:
        return {
            'success': False,
            'type': None,
            'data': {},
            'error': 'No QR code data provided'
        }
    
    try:
        # Look up QR code in database
        qr_code = QRCodeImage.objects.get(reference_id=qr_data)
        
        if qr_code.qr_type == 'personnel':
            return get_personnel_from_qr(qr_data)
        elif qr_code.qr_type == 'item':
            return get_item_from_qr(qr_data)
        else:
            return {
                'success': False,
                'type': None,
                'data': {},
                'error': f'Unknown QR code type: {qr_code.qr_type}'
            }
            
    except QRCodeImage.DoesNotExist:
        # QR code not in system, try direct ID lookup
        # First try personnel
        personnel_result = get_personnel_by_id(qr_data)
        if personnel_result['success']:
            return personnel_result
        
        # Then try item
        item_result = get_item_by_id(qr_data)
        if item_result['success']:
            return item_result
        
        return {
            'success': False,
            'type': None,
            'data': {},
            'error': 'QR code not found in system and does not match any personnel or item ID'
        }


def get_personnel_from_qr(qr_data):
    """
    Get personnel details from QR code data.
    
    Args:
        qr_data (str): QR code reference ID
        
    Returns:
        dict: Personnel details or error
    """
    try:
        personnel = Personnel.objects.get(id=qr_data)
        return {
            'success': True,
            'type': 'personnel',
            'data': {
                'id': personnel.id,
                'firstname': personnel.firstname,
                'surname': personnel.surname,
                'middle_initial': personnel.middle_initial or '',
                'full_name': personnel.get_full_name(),
                'rank': personnel.rank,
                'serial': personnel.serial,
                'office': personnel.office,
                'status': personnel.status,
            },
            'error': None
        }
    except Personnel.DoesNotExist:
        return {
            'success': False,
            'type': 'personnel',
            'data': {},
            'error': 'Personnel not found'
        }


def get_item_from_qr(qr_data):
    """
    Get item details from QR code data.
    
    Args:
        qr_data (str): QR code reference ID
        
    Returns:
        dict: Item details or error
    """
    try:
        item = Item.objects.get(id=qr_data)
        return {
            'success': True,
            'type': 'item',
            'data': {
                'id': item.id,
                'item_type': item.item_type,
                'serial': item.serial,
                'status': item.status,
                'condition': item.condition,
                'description': item.description or '',
            },
            'error': None
        }
    except Item.DoesNotExist:
        return {
            'success': False,
            'type': 'item',
            'data': {},
            'error': 'Item not found'
        }


def get_personnel_by_id(personnel_id):
    """
    Get personnel by direct ID lookup.
    
    Args:
        personnel_id (str): Personnel ID
        
    Returns:
        dict: Personnel details or error
    """
    try:
        personnel = Personnel.objects.get(id=personnel_id)
        return {
            'success': True,
            'type': 'personnel',
            'data': {
                'id': personnel.id,
                'firstname': personnel.firstname,
                'surname': personnel.surname,
                'middle_initial': personnel.middle_initial or '',
                'full_name': personnel.get_full_name(),
                'rank': personnel.rank,
                'serial': personnel.serial,
                'office': personnel.office,
                'status': personnel.status,
            },
            'error': None
        }
    except Personnel.DoesNotExist:
        return {
            'success': False,
            'type': 'personnel',
            'data': {},
            'error': 'Personnel not found'
        }


def get_item_by_id(item_id):
    """
    Get item by direct ID lookup.
    
    Args:
        item_id (str): Item ID
        
    Returns:
        dict: Item details or error
    """
    try:
        item = Item.objects.get(id=item_id)
        return {
            'success': True,
            'type': 'item',
            'data': {
                'id': item.id,
                'item_type': item.item_type,
                'serial': item.serial,
                'status': item.status,
                'condition': item.condition,
                'description': item.description or '',
            },
            'error': None
        }
    except Item.DoesNotExist:
        return {
            'success': False,
            'type': 'item',
            'data': {},
            'error': 'Item not found'
        }


def get_transaction_autofill_data(item_type, duty_type):
    """
    Get auto-fill data for transaction form based on item type and duty type.
    
    Args:
        item_type (str): Type of item (e.g., 'GLOCK', 'M16')
        duty_type (str): Type of duty (e.g., 'Duty Sentinel')
        
    Returns:
        dict: {
            'mags': int,
            'rounds': int
        }
    """
    autofill_rules = {
        ('GLOCK', 'Duty Sentinel'): {'mags': 4, 'rounds': 42},
        ('GLOCK', 'Duty Security'): {'mags': 3, 'rounds': 30},
        ('M16', 'Duty Sentinel'): {'mags': 3, 'rounds': 90},
        ('M16', 'Guard Duty'): {'mags': 2, 'rounds': 60},
        ('M4', 'Duty Sentinel'): {'mags': 3, 'rounds': 90},
        ('.45', 'Duty Sentinel'): {'mags': 3, 'rounds': 21},
    }
    
    # Normalize item type to uppercase
    item_type_upper = item_type.upper() if item_type else ''
    
    # Check for exact match
    key = (item_type_upper, duty_type)
    if key in autofill_rules:
        return autofill_rules[key]
    
    # Return empty values if no rule matches
    return {'mags': 0, 'rounds': 0}


def validate_transaction_action(item, action):
    """
    Validate if the requested action is allowed for the item's current status.
    
    Args:
        item (Item): Item instance
        action (str): 'Take' or 'Return'
        
    Returns:
        dict: {
            'valid': bool,
            'message': str
        }
    """
    if action == 'Take':
        if item.status == Item.STATUS_AVAILABLE:
            return {
                'valid': True,
                'message': f'Item {item.item_type} - {item.serial} is available for withdrawal'
            }
        else:
            return {
                'valid': False,
                'message': f'Cannot withdraw item. Current status: {item.status}. Item must be Available.'
            }
    
    elif action == 'Return':
        if item.status == Item.STATUS_ISSUED:
            return {
                'valid': True,
                'message': f'Item {item.item_type} - {item.serial} can be returned'
            }
        else:
            return {
                'valid': False,
                'message': f'Cannot return item. Current status: {item.status}. Item must be Issued.'
            }
    
    else:
        return {
            'valid': False,
            'message': f'Invalid action: {action}. Must be "Take" or "Return".'
        }
