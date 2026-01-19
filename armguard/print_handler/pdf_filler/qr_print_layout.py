"""
QR Print Layout Configuration
================================================================================
Adjust all print settings here: paper size, QR dimensions, card layout, spacing.
This configuration matches the existing HTML print layout from your screenshot.

ALL MEASUREMENTS IN MILLIMETERS for easy adjustment!
================================================================================
"""

# ==================== PRINT LAYOUT SETTINGS ====================
# Modify these values to customize your QR code print layout

# Paper Settings
PAPER_SIZE_NAME = 'A4'  # Options: 'A4', 'Letter', 'Legal'
PAGE_MARGIN_MM = 15  # Margin around the entire page (in mm)

# Card Settings (the bordered box containing each QR code)
CARD_WIDTH_MM = 50   # Width of each card (tighter fit)
CARD_HEIGHT_MM = 60  # Height of each card (tighter fit)
CARD_BORDER_WIDTH_PT = 2  # Border thickness (in points, 1pt ≈ 0.35mm)
CARD_BORDER_RADIUS_PT = 12  # Rounded corner radius
CARD_PADDING_MM = 2  # Internal padding inside the card (minimal)
CARD_PADDING_BOTTOM_MM = 4  # Double padding at the bottom

# QR Code Settings
QR_SIZE_MM = 20  # The QR code image size (20mm = 2cm - minimum for acceptable sharpness)
# Note: The actual QR PNG from media is 300x300px or 140x140px, 
# this setting controls how big it prints
# WARNING: QR codes smaller than 20mm may appear blurry due to downscaling

# Grid Layout
CARDS_PER_ROW = 3  # Number of cards horizontally per page (fits more with smaller cards)
HORIZONTAL_GAP_MM = 15  # Space between cards horizontally (reduced for compact layout)
VERTICAL_GAP_MM = 15  # Space between cards vertically (reduced for compact layout)

# Text/Font Settings
FONT_SIZE_ID = 11  # "ID: PE-994538041125" text size
FONT_SIZE_NAME = 12  # Name text size (e.g., "Mark Leo A. Pecate")
FONT_SIZE_BADGE = 10  # "PERSONNEL" or "ITEM" badge text size

# Colors (RGB values from 0.0 to 1.0)
TEXT_COLOR = (0, 0, 0)  # Black text
BADGE_BG_COLOR = (0.94, 0.94, 0.94)  # Light gray badge background
BADGE_BORDER_COLOR = (0.8, 0.8, 0.8)  # Badge border color
CARD_BORDER_COLOR = (0, 0, 0)  # Card border color (black)

# ==================== LAYOUT LOGIC (Don't modify unless needed) ====================

from reportlab.lib.pagesizes import A4, letter, legal
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
import os

# Paper size mapping
PAPER_SIZES = {
    'A4': A4,  # 210mm × 297mm
    'Letter': letter,  # 8.5" × 11" (216mm × 279mm)
    'Legal': legal,  # 8.5" × 14" (216mm × 356mm)
}

def get_layout_config():
    """
    Calculate and return the complete layout configuration.
    This function converts all MM measurements to points for ReportLab.
    """
    paper_size = PAPER_SIZES.get(PAPER_SIZE_NAME, A4)
    page_width, page_height = paper_size
    
    # Convert mm to points (ReportLab unit)
    margin = PAGE_MARGIN_MM * mm
    card_width = CARD_WIDTH_MM * mm
    card_height = CARD_HEIGHT_MM * mm
    card_padding = CARD_PADDING_MM * mm
    card_padding_bottom = CARD_PADDING_BOTTOM_MM * mm
    qr_size = QR_SIZE_MM * mm
    h_gap = HORIZONTAL_GAP_MM * mm
    v_gap = VERTICAL_GAP_MM * mm
    
    # Calculate usable page area
    usable_width = page_width - (2 * margin)
    usable_height = page_height - (2 * margin)
    
    # Calculate how many rows fit on one page
    rows_per_page = int((usable_height + v_gap) / (card_height + v_gap))
    
    # Calculate starting positions (top-left card)
    start_x = margin
    start_y = page_height - margin - card_height
    
    return {
        'paper_size': paper_size,
        'page_width': page_width,
        'page_height': page_height,
        'margin': margin,
        'card_width': card_width,
        'card_height': card_height,
        'card_padding': card_padding,
        'card_padding_bottom': card_padding_bottom,
        'card_border_width': CARD_BORDER_WIDTH_PT,
        'card_border_radius': CARD_BORDER_RADIUS_PT,
        'qr_size': qr_size,
        'cards_per_row': CARDS_PER_ROW,
        'rows_per_page': rows_per_page,
        'h_gap': h_gap,
        'v_gap': v_gap,
        'start_x': start_x,
        'start_y': start_y,
        'font_size_id': FONT_SIZE_ID,
        'font_size_name': FONT_SIZE_NAME,
        'font_size_badge': FONT_SIZE_BADGE,
        'text_color': TEXT_COLOR,
        'badge_bg_color': BADGE_BG_COLOR,
        'badge_border_color': BADGE_BORDER_COLOR,
        'card_border_color': CARD_BORDER_COLOR,
    }


# ==================== QUICK PRESETS ====================
# Use these to quickly switch between common layouts

PRESETS = {
    'default': {
        'PAPER_SIZE_NAME': 'A4',
        'CARD_WIDTH_MM': 95,
        'CARD_HEIGHT_MM': 110,
        'QR_SIZE_MM': 35,
        'CARDS_PER_ROW': 2,
        'HORIZONTAL_GAP_MM': 24,
        'VERTICAL_GAP_MM': 24,
    },
    'compact': {
        'PAPER_SIZE_NAME': 'A4',
        'CARD_WIDTH_MM': 70,
        'CARD_HEIGHT_MM': 90,
        'QR_SIZE_MM': 25,
        'CARDS_PER_ROW': 3,
        'HORIZONTAL_GAP_MM': 15,
        'VERTICAL_GAP_MM': 15,
    },
    'large': {
        'PAPER_SIZE_NAME': 'A4',
        'CARD_WIDTH_MM': 120,
        'CARD_HEIGHT_MM': 140,
        'QR_SIZE_MM': 50,
        'CARDS_PER_ROW': 1,
        'HORIZONTAL_GAP_MM': 20,
        'VERTICAL_GAP_MM': 20,
    },
    'us_letter_2col': {
        'PAPER_SIZE_NAME': 'Letter',
        'CARD_WIDTH_MM': 95,
        'CARD_HEIGHT_MM': 110,
        'QR_SIZE_MM': 35,
        'CARDS_PER_ROW': 2,
        'HORIZONTAL_GAP_MM': 20,
        'VERTICAL_GAP_MM': 20,
    },
}

def apply_preset(preset_name):
    """
    Apply a preset configuration by updating the global settings.
    Call this before generating the layout.
    """
    if preset_name in PRESETS:
        preset = PRESETS[preset_name]
        globals().update(preset)
        return True
    return False


# ==================== USAGE INSTRUCTIONS ====================
"""
HOW TO ADJUST THE PRINT LAYOUT:
================================

1. PAPER SIZE:
   - Change PAPER_SIZE_NAME to 'A4', 'Letter', or 'Legal'

2. QR CODE SIZE:
   - Change QR_SIZE_MM (in millimeters)
   - Example: 10mm = 1cm, 25mm = 2.5cm, 35mm = 3.5cm

3. CARD DIMENSIONS:
   - Change CARD_WIDTH_MM and CARD_HEIGHT_MM
   - Make sure cards fit on your paper!

4. CARDS PER ROW:
   - Change CARDS_PER_ROW (1, 2, 3, etc.)
   - Fewer cards = larger spacing

5. SPACING:
   - HORIZONTAL_GAP_MM: space between cards left-to-right
   - VERTICAL_GAP_MM: space between cards top-to-bottom

6. MARGINS:
   - PAGE_MARGIN_MM: margin around entire page

7. USE A PRESET:
   - Call apply_preset('compact') or apply_preset('large') before rendering

EXAMPLE:
--------
from print_handler.pdf_filler.qr_print_layout import apply_preset, get_layout_config

# Use compact preset
apply_preset('compact')

# Or customize individual settings
from print_handler.pdf_filler import qr_print_layout
qr_print_layout.QR_SIZE_MM = 40
qr_print_layout.CARDS_PER_ROW = 3

# Get the calculated layout
config = get_layout_config()
"""


def generate_qr_print_pdf(qr_images, output_path, paper_size=A4, qr_size_mm=30, margin_mm=15, columns=3, rows=5):
    """
    Generate a PDF file with QR code images arranged in a grid.
    
    Args:
        qr_images (list): List of file paths to QR code images
        output_path (str): Path where the PDF will be saved
        paper_size (tuple): ReportLab paper size (default: A4)
        qr_size_mm (int): QR code size in millimeters (default: 30)
        margin_mm (int): Page margin in millimeters (default: 15)
        columns (int): Number of columns per page (default: 3)
        rows (int): Number of rows per page (default: 5)
    
    Returns:
        str: Path to the generated PDF file
    """
    # Convert mm to points
    qr_size = qr_size_mm * mm
    margin = margin_mm * mm
    
    # Calculate spacing
    page_width, page_height = paper_size
    usable_width = page_width - (2 * margin)
    usable_height = page_height - (2 * margin)
    
    h_gap = (usable_width - (columns * qr_size)) / (columns + 1)
    v_gap = (usable_height - (rows * qr_size)) / (rows + 1)
    
    # Create PDF
    c = canvas.Canvas(output_path, pagesize=paper_size)
    
    # Track position
    qr_index = 0
    total_qrs = len(qr_images)
    
    while qr_index < total_qrs:
        # Draw QR codes for this page
        for row in range(rows):
            for col in range(columns):
                if qr_index >= total_qrs:
                    break
                
                # Calculate position (top-left origin)
                x = margin + (col * (qr_size + h_gap)) + h_gap
                y = page_height - margin - ((row + 1) * (qr_size + v_gap))
                
                # Draw QR image
                qr_image_path = qr_images[qr_index]
                if os.path.exists(qr_image_path):
                    try:
                        c.drawImage(
                            qr_image_path,
                            x, y,
                            width=qr_size,
                            height=qr_size,
                            preserveAspectRatio=True
                        )
                    except Exception as e:
                        # Draw placeholder if image fails
                        c.setStrokeColorRGB(0.5, 0.5, 0.5)
                        c.setFillColorRGB(0.9, 0.9, 0.9)
                        c.rect(x, y, qr_size, qr_size, fill=1)
                        c.setFillColorRGB(0, 0, 0)
                        c.setFont("Helvetica", 8)
                        c.drawCentredString(x + qr_size/2, y + qr_size/2, "Error loading QR")
                
                qr_index += 1
            
            if qr_index >= total_qrs:
                break
        
        # Add new page if more QR codes remain
        if qr_index < total_qrs:
            c.showPage()
    
    # Save PDF
    c.save()
    return output_path
