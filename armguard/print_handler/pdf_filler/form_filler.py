"""
PDF Form Filler for Temp_Rec.pdf
Fills transaction forms with actual data during normal transactions
Uses PyMuPDF to overlay text on the PDF template
"""
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    import warnings
    warnings.warn("PyMuPDF not available. PDF form filling will be limited.")
    
from io import BytesIO
import os
from django.conf import settings
from .form_config import (
    VERTICAL_OFFSET, HORIZONTAL_OFFSET, UPPER_FORM, 
    LOWER_FORM_Y_OFFSET, FONT_NAME, FONT_COLOR, FIELD_ADJUSTMENTS, ROTATION
)


class TransactionFormFiller:
    """Fills Temp_Rec.pdf form with transaction data by overlaying text"""
    
    def __init__(self):
        self.template_path = os.path.join(
            settings.BASE_DIR, 
            'print_handler', 
            'templates', 
            'pdf_forms', 
            'Temp_Rec.pdf'
        )
    
    def fill_transaction_form(self, transaction):
        """
        Fill the Temp_Rec.pdf form with transaction data by overlaying text
        
        Args:
            transaction: Transaction model instance
            
        Returns:
            BytesIO: Filled PDF as bytes
        """
        if not PYMUPDF_AVAILABLE:
            # Fallback to basic PDF handling without form filling
            import warnings
            warnings.warn("PyMuPDF not available - returning template without form data")
            
            try:
                with open(self.template_path, 'rb') as f:
                    pdf_bytes = BytesIO(f.read())
                return pdf_bytes
            except FileNotFoundError:
                # Return empty BytesIO if template not found
                return BytesIO()
        
        # Open the PDF template
        template_doc = fitz.open(self.template_path)
        
        # Create new document with shifted content if needed
        if VERTICAL_OFFSET != 0:
            doc = self._create_shifted_pdf(template_doc)
            template_doc.close()
        else:
            doc = template_doc
        
        page = doc[0]  # First page
        
        # Prepare data
        data = self._prepare_data(transaction)
        
        # Add text overlays based on Temp_Rec.pdf layout
        # You'll need to adjust coordinates based on actual PDF layout
        self._add_text_overlays(page, data)
        
        # Save to BytesIO
        output = BytesIO()
        output.write(doc.tobytes())
        output.seek(0)
        doc.close()
        
        return output
    
    def _create_shifted_pdf(self, source_doc):
        """
        Create a new PDF with content shifted down by VERTICAL_OFFSET
        This moves the logo and all background elements down to prevent cutting
        Uses Legal paper size (8.5" x 14" = 612 x 1008 points)
        Can optionally rotate 180 degrees to swap top/bottom margins
        No scaling - uses exact coordinates
        """
        # Create new empty document
        new_doc = fitz.open()
        
        # Get source page dimensions
        source_page = source_doc[0]
        source_rect = source_page.rect
        
        # Use Legal paper size (14 inches = 1008 points)
        # Standard US Legal: 8.5" x 14" = 612 x 1008 points
        legal_width = 612
        legal_height = 1008
        new_page = new_doc.new_page(width=legal_width, height=legal_height)
        
        # Set page size explicitly in multiple ways for printer compatibility
        new_page.set_mediabox(fitz.Rect(0, 0, legal_width, legal_height))
        
        # Draw white background
        new_page.draw_rect(fitz.Rect(0, 0, legal_width, legal_height),
                          color=None, fill=(1, 1, 1))
        
        # Copy source page content to new page, shifted down
        # The content will be positioned starting at VERTICAL_OFFSET from top
        target_rect = fitz.Rect(0, VERTICAL_OFFSET, source_rect.width, VERTICAL_OFFSET + source_rect.height)
        new_page.show_pdf_page(target_rect, source_doc, 0)
        
        # Apply rotation if configured (180 degrees swaps top/bottom margins)
        if ROTATION == 180:
            new_page.set_rotation(180)
        
        # Set document metadata to indicate Legal paper
        new_doc.set_metadata({
            'title': 'Transaction Receipt - Legal Size',
            'producer': 'ArmGuard System'
        })
        
        return new_doc
        
        return new_doc
    
    def _prepare_data(self, transaction):
        """Prepare transaction data for display"""
        personnel = transaction.personnel
        item = transaction.item
        
        # Format personnel name without period in middle initial
        if personnel.middle_initial:
            personnel_name = f"{personnel.firstname} {personnel.middle_initial} {personnel.surname}"
        else:
            personnel_name = f"{personnel.firstname} {personnel.surname}"
        
        # Format issuer
        if transaction.issued_by and hasattr(transaction.issued_by, 'personnel'):
            issuer_personnel = transaction.issued_by.personnel
            issued_by = f"{issuer_personnel.rank} {issuer_personnel.firstname} {issuer_personnel.surname} {issuer_personnel.serial} PAF"
        else:
            issued_by = transaction.issued_by.get_full_name() if transaction.issued_by else "N/A"
        
        transaction_mode = (getattr(transaction, 'transaction_mode', '') or '').lower()
        purpose_value = 'DEFCON' if transaction_mode == 'defcon' else (transaction.duty_type or 'duty security')

        return {
            'date': transaction.date_time.strftime('%d/%m/%Y'),
            'time': transaction.date_time.strftime('%H:%M:%S'),
            'transaction_id': str(transaction.id),
            'personnel_name': personnel_name,
            'personnel_rank': personnel.rank or '',
            'personnel_serial': personnel.get_serial_display(),
            'personnel_unit': personnel.group,
            'personnel_tel': personnel.tel or '',
            'personnel_full': f"{personnel.rank} {personnel.firstname} {personnel.surname} {personnel.get_serial_display()} PAF",
            'item_type': item.item_type,
            'item_serial': item.serial,
            'item_condition': item.condition,
            'action': transaction.action,
            'mags': str(transaction.mags) if transaction.mags else '0',
            'rounds': str(transaction.rounds) if transaction.rounds else '0',
            'duty_type': purpose_value,
            'notes': transaction.notes or '',
            'issued_by': issued_by,
        }
    
    def _add_text_overlays(self, page, data):
        """
        Add text overlays to the PDF page
        Based on Temp_Rec.pdf analysis - form has 2 identical sections (top and bottom)
        Coordinates: Origin (0,0) at TOP-LEFT, Y increases downward
        Page size: 612 x 936 points
        """
        # Fill top form
        self._fill_upper_form(page, data)
        
        # Fill bottom form
        self._fill_lower_form(page, data)
    
    def _apply_offsets(self, x, y, field_name=None):
        """Apply global and field-specific offsets to coordinates"""
        # Apply global offsets
        x += HORIZONTAL_OFFSET
        y += VERTICAL_OFFSET
        
        # Apply field-specific adjustments if configured
        if field_name and field_name in FIELD_ADJUSTMENTS:
            x += FIELD_ADJUSTMENTS[field_name].get('x', 0)
            y += FIELD_ADJUSTMENTS[field_name].get('y', 0)
        
        return (x, y)
    
    def _fill_upper_form(self, page, data):
        """Fill the upper form section with configurable positions"""
        # Date field (top right)
        pos = self._apply_offsets(UPPER_FORM['date']['x'], UPPER_FORM['date']['y'], 'date')
        page.insert_text(pos, data['date'], fontsize=UPPER_FORM['date']['size'], 
                        fontname=FONT_NAME, color=FONT_COLOR)
        
        # Personnel information line
        pos = self._apply_offsets(UPPER_FORM['personnel_name']['x'], UPPER_FORM['personnel_name']['y'], 'personnel_name')
        page.insert_text(pos, data['personnel_name'], fontsize=UPPER_FORM['personnel_name']['size'], 
                        fontname=FONT_NAME, color=FONT_COLOR)
        
        pos = self._apply_offsets(UPPER_FORM['personnel_rank']['x'], UPPER_FORM['personnel_rank']['y'], 'personnel_rank')
        page.insert_text(pos, data['personnel_rank'], fontsize=UPPER_FORM['personnel_rank']['size'], 
                        fontname=FONT_NAME, color=FONT_COLOR)
        
        pos = self._apply_offsets(UPPER_FORM['personnel_serial']['x'], UPPER_FORM['personnel_serial']['y'], 'personnel_serial')
        page.insert_text(pos, data['personnel_serial'], fontsize=UPPER_FORM['personnel_serial']['size'], 
                        fontname=FONT_NAME, color=FONT_COLOR)
        
        pos = self._apply_offsets(UPPER_FORM['personnel_unit']['x'], UPPER_FORM['personnel_unit']['y'], 'personnel_unit')
        page.insert_text(pos, data['personnel_unit'], fontsize=UPPER_FORM['personnel_unit']['size'], 
                        fontname=FONT_NAME, color=FONT_COLOR)
        
        # Item classification and ammunition
        pos = self._apply_offsets(UPPER_FORM['item_type']['x'], UPPER_FORM['item_type']['y'], 'item_type')
        page.insert_text(pos, data['item_type'], fontsize=UPPER_FORM['item_type']['size'], 
                        fontname=FONT_NAME, color=FONT_COLOR)
        
        pos = self._apply_offsets(UPPER_FORM['mags']['x'], UPPER_FORM['mags']['y'], 'mags')
        page.insert_text(pos, data['mags'], fontsize=UPPER_FORM['mags']['size'], 
                        fontname=FONT_NAME, color=FONT_COLOR)
        
        pos = self._apply_offsets(UPPER_FORM['rounds']['x'], UPPER_FORM['rounds']['y'], 'rounds')
        page.insert_text(pos, data['rounds'], fontsize=UPPER_FORM['rounds']['size'], 
                        fontname=FONT_NAME, color=FONT_COLOR)
        
        # Number of items and serial number
        pos = self._apply_offsets(UPPER_FORM['nr_of_items']['x'], UPPER_FORM['nr_of_items']['y'], 'nr_of_items')
        page.insert_text(pos, "1", fontsize=UPPER_FORM['nr_of_items']['size'], 
                        fontname=FONT_NAME, color=FONT_COLOR)
        
        pos = self._apply_offsets(UPPER_FORM['item_serial']['x'], UPPER_FORM['item_serial']['y'], 'item_serial')
        page.insert_text(pos, data['item_serial'], fontsize=UPPER_FORM['item_serial']['size'], 
                        fontname=FONT_NAME, color=FONT_COLOR)
        
        # Purpose and telephone
        pos = self._apply_offsets(UPPER_FORM['duty_type']['x'], UPPER_FORM['duty_type']['y'], 'duty_type')
        page.insert_text(pos, data['duty_type'], fontsize=UPPER_FORM['duty_type']['size'], 
                        fontname=FONT_NAME, color=FONT_COLOR)
        
        pos = self._apply_offsets(UPPER_FORM['personnel_tel']['x'], UPPER_FORM['personnel_tel']['y'], 'personnel_tel')
        page.insert_text(pos, data['personnel_tel'], fontsize=UPPER_FORM['personnel_tel']['size'], 
                        fontname=FONT_NAME, color=FONT_COLOR)
        
        # Signatures
        pos = self._apply_offsets(UPPER_FORM['received_by']['x'], UPPER_FORM['received_by']['y'], 'received_by')
        page.insert_text(pos, data['personnel_full'], fontsize=UPPER_FORM['received_by']['size'], 
                        fontname=FONT_NAME, color=FONT_COLOR)
        
        pos = self._apply_offsets(UPPER_FORM['issued_by']['x'], UPPER_FORM['issued_by']['y'], 'issued_by')
        page.insert_text(pos, data['issued_by'], fontsize=UPPER_FORM['issued_by']['size'], 
                        fontname=FONT_NAME, color=FONT_COLOR)
    
    def _fill_lower_form(self, page, data):
        """Fill the lower form section with configurable positions"""
        # Apply lower form offset
        y_offset = LOWER_FORM_Y_OFFSET
        
        # Date field (top right)
        pos = self._apply_offsets(UPPER_FORM['date']['x'], UPPER_FORM['date']['y'] + y_offset, 'date')
        page.insert_text(pos, data['date'], fontsize=UPPER_FORM['date']['size'], 
                        fontname=FONT_NAME, color=FONT_COLOR)
        
        # Personnel information line
        pos = self._apply_offsets(UPPER_FORM['personnel_name']['x'], UPPER_FORM['personnel_name']['y'] + y_offset, 'personnel_name')
        page.insert_text(pos, data['personnel_name'], fontsize=UPPER_FORM['personnel_name']['size'], 
                        fontname=FONT_NAME, color=FONT_COLOR)
        
        pos = self._apply_offsets(UPPER_FORM['personnel_rank']['x'], UPPER_FORM['personnel_rank']['y'] + y_offset, 'personnel_rank')
        page.insert_text(pos, data['personnel_rank'], fontsize=UPPER_FORM['personnel_rank']['size'], 
                        fontname=FONT_NAME, color=FONT_COLOR)
        
        pos = self._apply_offsets(UPPER_FORM['personnel_serial']['x'], UPPER_FORM['personnel_serial']['y'] + y_offset, 'personnel_serial')
        page.insert_text(pos, data['personnel_serial'], fontsize=UPPER_FORM['personnel_serial']['size'], 
                        fontname=FONT_NAME, color=FONT_COLOR)
        
        pos = self._apply_offsets(UPPER_FORM['personnel_unit']['x'], UPPER_FORM['personnel_unit']['y'] + y_offset, 'personnel_unit')
        page.insert_text(pos, data['personnel_unit'], fontsize=UPPER_FORM['personnel_unit']['size'], 
                        fontname=FONT_NAME, color=FONT_COLOR)
        
        # Item classification and ammunition
        pos = self._apply_offsets(UPPER_FORM['item_type']['x'], UPPER_FORM['item_type']['y'] + y_offset, 'item_type')
        page.insert_text(pos, data['item_type'], fontsize=UPPER_FORM['item_type']['size'], 
                        fontname=FONT_NAME, color=FONT_COLOR)
        
        pos = self._apply_offsets(UPPER_FORM['mags']['x'], UPPER_FORM['mags']['y'] + y_offset, 'mags')
        page.insert_text(pos, data['mags'], fontsize=UPPER_FORM['mags']['size'], 
                        fontname=FONT_NAME, color=FONT_COLOR)
        
        pos = self._apply_offsets(UPPER_FORM['rounds']['x'], UPPER_FORM['rounds']['y'] + y_offset, 'rounds')
        page.insert_text(pos, data['rounds'], fontsize=UPPER_FORM['rounds']['size'], 
                        fontname=FONT_NAME, color=FONT_COLOR)
        
        # Number of items and serial number
        pos = self._apply_offsets(UPPER_FORM['nr_of_items']['x'], UPPER_FORM['nr_of_items']['y'] + y_offset, 'nr_of_items')
        page.insert_text(pos, "1", fontsize=UPPER_FORM['nr_of_items']['size'], 
                        fontname=FONT_NAME, color=FONT_COLOR)
        
        pos = self._apply_offsets(UPPER_FORM['item_serial']['x'], UPPER_FORM['item_serial']['y'] + y_offset, 'item_serial')
        page.insert_text(pos, data['item_serial'], fontsize=UPPER_FORM['item_serial']['size'], 
                        fontname=FONT_NAME, color=FONT_COLOR)
        
        # Purpose and telephone
        pos = self._apply_offsets(UPPER_FORM['duty_type']['x'], UPPER_FORM['duty_type']['y'] + y_offset, 'duty_type')
        page.insert_text(pos, data['duty_type'], fontsize=UPPER_FORM['duty_type']['size'], 
                        fontname=FONT_NAME, color=FONT_COLOR)
        
        pos = self._apply_offsets(UPPER_FORM['personnel_tel']['x'], UPPER_FORM['personnel_tel']['y'] + y_offset, 'personnel_tel')
        page.insert_text(pos, data['personnel_tel'], fontsize=UPPER_FORM['personnel_tel']['size'], 
                        fontname=FONT_NAME, color=FONT_COLOR)
        
        # Signatures (note: lower form signature position is slightly different)
        pos = self._apply_offsets(UPPER_FORM['received_by']['x'], UPPER_FORM['received_by']['y'] + y_offset - 10, 'received_by')
        page.insert_text(pos, data['personnel_full'], fontsize=UPPER_FORM['received_by']['size'], 
                        fontname=FONT_NAME, color=FONT_COLOR)
        
        pos = self._apply_offsets(UPPER_FORM['issued_by']['x'], UPPER_FORM['issued_by']['y'] + y_offset - 10, 'issued_by')
        page.insert_text(pos, data['issued_by'], fontsize=UPPER_FORM['issued_by']['size'], 
                        fontname=FONT_NAME, color=FONT_COLOR)
    
    def get_page_info(self):
        """
        Get PDF page dimensions and info for coordinate mapping
        Useful for debugging text placement
        """
        doc = fitz.open(self.template_path)
        page = doc[0]
        info = {
            'width': page.rect.width,
            'height': page.rect.height,
            'rotation': page.rotation,
        }
        doc.close()
        return info
