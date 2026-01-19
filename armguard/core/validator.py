"""
Validators for ArmGuard models
"""


def validate_item_data(item):
    """
    Validate item data before saving
    Returns list of errors if any, empty list if valid
    """
    errors = []
    
    # Check if item_type is set
    if not item.item_type:
        errors.append("Item type is required")
    
    # Check if serial is set
    if not item.serial:
        errors.append("Serial number is required")
    
    # Check serial uniqueness (will be handled by database unique constraint)
    
    return errors


def validate_personnel_data(personnel):
    """
    Validate personnel data before saving
    Returns list of errors if any, empty list if valid
    """
    errors = []
    
    # Check required fields
    if not personnel.surname:
        errors.append("Surname is required")
    
    if not personnel.firstname:
        errors.append("First name is required")
    
    if not personnel.rank:
        errors.append("Rank is required")
    
    if not personnel.serial:
        errors.append("Serial number is required")
    
    if not personnel.office:
        errors.append("Office is required")
    
    if not personnel.tel:
        errors.append("Telephone is required")
    
    return errors
