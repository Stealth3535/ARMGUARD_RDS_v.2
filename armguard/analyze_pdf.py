"""Analyze Temp_Rec.pdf structure to find proper text placement"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

import fitz  # PyMuPDF
from django.conf import settings

# Open the template PDF
template_path = os.path.join(
    settings.BASE_DIR, 
    'print_handler', 
    'templates', 
    'pdf_forms', 
    'Temp_Rec.pdf'
)

doc = fitz.open(template_path)
page = doc[0]

print(f"PDF Information:")
print(f"  Pages: {len(doc)}")
print(f"  Page size: {page.rect.width} x {page.rect.height} points")
print(f"  Rotation: {page.rotation}")
print()

# Extract all text with positions
print("Text blocks on page:")
print("-" * 80)
blocks = page.get_text("dict")["blocks"]

for block in blocks:
    if block.get("type") == 0:  # Text block
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text = span.get("text", "").strip()
                if text:
                    bbox = span.get("bbox")  # (x0, y0, x1, y1)
                    size = span.get("size")
                    print(f"  Position: ({bbox[0]:.1f}, {bbox[1]:.1f}) | Size: {size:.1f} | Text: '{text}'")

print("-" * 80)
print()

# Get images/drawings
print("Images/Graphics on page:")
images = page.get_images()
print(f"  Total images: {len(images)}")

# Get drawings
drawings = page.get_drawings()
print(f"  Total drawings/lines: {len(drawings)}")

doc.close()

print()
print("Coordinate system notes:")
print("  - Origin (0,0) is at TOP-LEFT corner")
print("  - X increases to the right")
print("  - Y increases downward")
print("  - Page dimensions: 612 x 936 points (Letter size)")
