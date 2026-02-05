# Print Handler App

## Overview
The Print Handler app provides printing functionality for QR codes and transaction forms in the ArmGuard system.

## Features

### 1. QR Code Printing
- **Print All QR Codes**: `/print/qr-codes/`
  - Displays all personnel and item QR codes in a printable grid layout
  - Automatically formatted for print media
  - **Layout controlled by Python configuration** - see [QR Print Layout Configuration](#qr-print-layout-configuration) below
  
- **Print Single QR Code**: `/print/qr-codes/<qr_id>/`
  - Prints a single QR code with detailed information
  - Large format suitable for labels

### 2. Transaction Form Printing
- **Blank Transaction Form**: `/print/transaction-form/`
  - Generates a blank transaction form for manual filling
  
- **Filled Transaction Form**: `/print/transaction-form/<transaction_id>/`
  - Generates a pre-filled transaction form from database
  - Includes personnel, item, and transaction details
  
- **Transaction History Report**: `/print/transactions/`
  - Prints a list of all transactions
  - Supports filtering by personnel or item using query parameters:
    - `?personnel_id=<id>` - Filter by personnel
    - `?item_id=<id>` - Filter by item

### 3. PDF Generation
The `pdf_filler` module provides programmatic PDF generation using ReportLab:

```python
from print_handler.pdf_filler.pdf_filler1 import PDFFiller

# Create a PDF transaction form
pdf_filler = PDFFiller()
pdf_content = pdf_filler.create_transaction_form(transaction)

# Create a QR code label
pdf_content = pdf_filler.create_qr_label(qr_code)
```

## URLs

| URL Pattern | View Function | Description |
|-------------|---------------|-------------|
| `/print/qr-codes/` | `print_qr_codes` | Print all QR codes |
| `/print/qr-codes/<id>/` | `print_single_qr` | Print single QR code |
| `/print/transaction-form/` | `print_transaction_form` | Blank transaction form |
| `/print/transaction-form/<id>/` | `print_transaction_form` | Filled transaction form |
| `/print/transactions/` | `print_all_transactions` | Transaction history report |

## Templates

### Print Handler Templates
Located in `print_handler/templates/print_handler/`:
- `print_qr_codes.html` - Grid view of all QR codes
- `print_single_qr.html` - Single QR code with details
- `print_transaction_form.html` - Transaction form layout
- `print_transactions.html` - Transaction history table

### PDF Form Templates
Located in `print_handler/templates/pdf_forms/`:
- `transaction_form_template.html` - Base template for PDF forms

## Styling

All templates include print-specific CSS that:
- Hides navigation and buttons when printing
- Optimizes layout for paper
- Ensures proper page breaks
- Uses high-contrast colors for clarity

---

## QR Print Layout Configuration

### Overview
The QR code printing system uses a **Python-based configuration file** that allows you to easily adjust:
- Paper size (A4, Letter, Legal)
- Card dimensions
- QR code size
- Number of cards per row
- Spacing and gaps
- Font sizes
- Colors

**All measurements are in millimeters** for easy real-world sizing!

### Configuration File Location
📁 `print_handler/pdf_filler/qr_print_layout.py`

### Current Configuration

Run this command to see your current settings:
```bash
python test_layout.py
```

Example output:
```
=== QR Print Layout Configuration ===
Paper Size: A4
Card Size: 95mm x 110mm
QR Size: 35mm
Cards Per Row: 2
Gap: H=24mm, V=24mm
Calculated rows per page: 2
✓ Configuration loaded successfully!
```

### How to Adjust Layout Settings

**1. Open the configuration file:**
```bash
# Edit this file to change print layout
print_handler/pdf_filler/qr_print_layout.py
```

**2. Key Settings (All in Millimeters):**

```python
# Paper Configuration
PAPER_SIZE_NAME = 'A4'  # Options: 'A4', 'LETTER', 'LEGAL'
PAGE_MARGIN_MM = 15      # Margins around the page

# Card Dimensions
CARD_WIDTH_MM = 95       # Width of each QR card
CARD_HEIGHT_MM = 110     # Height of each QR card

# QR Code Settings
QR_SIZE_MM = 35          # Size of the QR code image

# Layout Grid
CARDS_PER_ROW = 2        # How many cards fit horizontally
HORIZONTAL_GAP_MM = 24   # Space between cards (horizontal)
VERTICAL_GAP_MM = 24     # Space between cards (vertical)

# Styling
CARD_BORDER_WIDTH_PT = 2 # Border thickness (in points)
CARD_BORDER_COLOR = '#ddd'
CARD_BACKGROUND = 'white'

# Font Sizes
FONT_SIZE_ID = 11        # ID/Serial text size
FONT_SIZE_NAME = 12      # Name text size
FONT_SIZE_BADGE = 10     # Badge number text size
```

**3. Save the file and refresh your browser** - changes take effect immediately!

### Common Adjustments

#### Make QR Codes Larger
```python
QR_SIZE_MM = 50  # Increase from 35mm to 50mm
```

#### Fit More Cards Per Page (Compact Layout)
```python
CARD_WIDTH_MM = 70       # Smaller cards
CARD_HEIGHT_MM = 85
QR_SIZE_MM = 25          # Smaller QR codes
CARDS_PER_ROW = 3        # 3 cards per row instead of 2
HORIZONTAL_GAP_MM = 10   # Reduce gaps
VERTICAL_GAP_MM = 10
```

#### Use US Letter Paper (Instead of A4)
```python
PAPER_SIZE_NAME = 'LETTER'
```

#### Larger Cards for Wall Mounting
```python
CARD_WIDTH_MM = 140
CARD_HEIGHT_MM = 160
QR_SIZE_MM = 60
CARDS_PER_ROW = 1  # One large card per row
```

### Using Layout Presets

The configuration file includes ready-made presets:

```python
from print_handler.pdf_filler.qr_print_layout import get_layout_config

# Get default configuration
layout = get_layout_config()

# Or use a preset:
layout = get_layout_config(preset='compact')   # More cards per page
layout = get_layout_config(preset='large')     # Larger QR codes
layout = get_layout_config(preset='us_letter_2col')  # US Letter, 2 columns
```

### Why Python Configuration Instead of HTML/CSS?

✅ **Real-world measurements** - Use millimeters/inches, not pixels  
✅ **One place to edit** - All settings in a single file  
✅ **Paper-aware** - Automatically calculates how many cards fit  
✅ **Easy to test** - Run `python test_layout.py` to preview changes  
✅ **Version control friendly** - Simple Python file, easy to track changes  

### Files Involved

| File | Purpose |
|------|---------|
| `pdf_filler/qr_print_layout.py` | **Main configuration file** - Edit this to change layout |
| `views.py` | Loads configuration and passes to template |
| `templates/print_qr_codes.html` | Uses `{{ layout.* }}` variables from Python |
| `test_layout.py` | Test script to display current configuration |

### Support

If you need help adjusting the layout:
1. Run `python test_layout.py` to see current settings
2. Edit values in `qr_print_layout.py`
3. Save and refresh your browser
4. If cards don't fit, the system will calculate and show how many fit per page

---

## Usage Examples

### From Templates
Add print buttons to your existing pages:

```html
<!-- Print single QR code -->
<a href="{% url 'print_handler:print_single_qr' qr_code.id %}" class="btn btn-primary" target="_blank">
    🖨️ Print QR Code
</a>

<!-- Print transaction form -->
<a href="{% url 'print_handler:print_transaction_form_detail' transaction.id %}" class="btn btn-primary" target="_blank">
    🖨️ Print Form
</a>
```

### From Views
Generate PDFs programmatically:

```python
from django.http import HttpResponse
from print_handler.pdf_filler.pdf_filler1 import PDFFiller
from transactions.models import Transaction

def download_transaction_pdf(request, transaction_id):
    transaction = Transaction.objects.get(id=transaction_id)
    pdf_filler = PDFFiller()
    pdf_content = pdf_filler.create_transaction_form(transaction)
    
    response = HttpResponse(pdf_content, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="transaction_{transaction_id}.pdf"'
    return response
```

## Print Tips

1. **For best results**, use the browser's print dialog:
   - Press Ctrl+P (Windows) or Cmd+P (Mac)
   - Or click the 🖨️ Print button on the page

2. **QR Code printing**:
   - Recommended paper size: A4 or Letter
   - Orientation: Portrait
   - Margins: Default

3. **Transaction forms**:
   - Recommended paper size: A4 or Letter
   - Orientation: Portrait for forms, Landscape for transaction history
   - Consider saving as PDF for archiving

## Dependencies

Required Python packages:
- `reportlab` - For PDF generation

Install with:
```bash
pip install reportlab
```

## Future Enhancements

Potential improvements:
- [ ] Add barcode support alongside QR codes
- [ ] Custom PDF templates for different transaction types
- [ ] Batch printing with multiple items per page
- [ ] Print queue management
- [ ] Custom header/footer with organization logo
- [ ] Digital signatures on PDF forms
