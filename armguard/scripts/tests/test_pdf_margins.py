"""
Test PDF Page Margins and Print Area
Checks if the PDF content is within printer's printable area
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

import fitz
from django.conf import settings

def main():
    print("\n" + "="*80)
    print("  PDF MARGIN ANALYSIS")
    print("="*80)
    
    # Open the template PDF
    template_path = os.path.join(
        settings.BASE_DIR, 
        'print_handler', 
        'templates', 
        'pdf_forms', 
        'Temp_Rec.pdf'
    )
    
    if not os.path.exists(template_path):
        print(f"✗ Template not found: {template_path}")
        return False
    
    doc = fitz.open(template_path)
    page = doc[0]
    
    print(f"\n--- PDF Page Information ---")
    print(f"Page size: {page.rect.width} x {page.rect.height} points")
    print(f"Page size: {page.rect.width/72:.2f}\" x {page.rect.height/72:.2f}\" inches")
    print(f"Expected: 8.5\" x 14\" (Legal size)")
    print(f"Rotation: {page.rotation}°")
    
    # Check current text positions
    print(f"\n--- Current Text Positions (Upper Form) ---")
    print(f"Date field: Y = 116 points ({116/72:.2f}\" from top)")
    print(f"Personnel name: Y = 160 points ({160/72:.2f}\" from top)")
    print(f"First data row: Y = 193 points ({193/72:.2f}\" from top)")
    
    # Typical printer margins
    print(f"\n--- Typical Printer Margins ---")
    print(f"Top margin: 0.25\" to 0.5\" (18-36 points)")
    print(f"Left margin: 0.25\" (18 points)")
    print(f"Right margin: 0.25\" (18 points)")
    print(f"Bottom margin: 0.25\" to 0.5\" (18-36 points)")
    
    print(f"\n--- Problem Analysis ---")
    top_content = 116  # First content position
    min_printer_margin = 36  # 0.5 inch typical top margin
    
    if top_content < min_printer_margin:
        gap = min_printer_margin - top_content
        print(f"⚠ WARNING: Content starts at {top_content} points")
        print(f"  Printer minimum top margin: {min_printer_margin} points")
        print(f"  Content is {gap} points ({gap/72:.2f}\") TOO HIGH!")
        print(f"  This will cause top content to be cut off when printing")
    else:
        print(f"✓ Content starts at safe position")
    
    # Check for header/logo area
    print(f"\n--- Template Analysis ---")
    print(f"Looking for text objects in top area (0-100 points)...")
    
    # Extract text to see what's in the top area
    text_instances = page.get_text("dict")
    
    top_area_text = []
    for block in text_instances.get("blocks", []):
        if block.get("type") == 0:  # Text block
            for line in block.get("lines", []):
                y = line.get("bbox", [0, 0, 0, 0])[1]
                if y < 120:  # Top area
                    for span in line.get("spans", []):
                        top_area_text.append({
                            'text': span.get("text", ""),
                            'y': y,
                            'size': span.get("size", 0)
                        })
    
    if top_area_text:
        print(f"Found {len(top_area_text)} text elements in top area:")
        for item in top_area_text[:10]:  # Show first 10
            print(f"  Y={item['y']:.1f} Size={item['size']:.1f} Text=\"{item['text']}\"")
    else:
        print("No text found in top area (0-120 points)")
    
    doc.close()
    
    print(f"\n--- Recommendation ---")
    print(f"✓ Option 1: Adjust @page margin in pdf_print.html")
    print(f"  Change: margin: 0; → margin: 0.5in 0.25in;")
    print(f"  Pros: Respects printer margins, no PDF modification")
    print(f"  Cons: May not print template header/logo area")
    
    print(f"\n✓ Option 2: Keep margin: 0 (current)")
    print(f"  Pros: Attempts to print entire PDF including header")
    print(f"  Cons: Printer will clip top margin automatically")
    print(f"  Note: Most printers enforce minimum margins regardless of PDF settings")
    
    print(f"\n✓ Option 3: Use 'Fit to Page' printer setting")
    print(f"  User must select 'Fit' or 'Shrink to fit' in print dialog")
    print(f"  This scales the PDF to fit within printable area")
    
    print(f"\n💡 RECOMMENDED FIX:")
    print(f"  Update pdf_print.html to add CSS hint for scaling:")
    print(f"  @page {{ size: legal; margin: 0.5in 0.25in; }}")
    print(f"  And add user instruction to select 'Fit to page' in print dialog")
    
    print("\n" + "="*80)
    return True

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
