"""
PDF Position Adjustment Tool
Use this to test different VERTICAL_OFFSET values and see the results
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from transactions.models import Transaction
from django.conf import settings
from print_handler.pdf_filler.form_filler import TransactionFormFiller
import importlib

def reload_config():
    """Reload the configuration module"""
    import print_handler.pdf_filler.form_config as config
    importlib.reload(config)
    return config

def generate_test_pdf(offset_value, transaction):
    """Generate a test PDF with specific offset"""
    # Update the config file
    config_path = os.path.join(
        settings.BASE_DIR,
        'print_handler',
        'pdf_filler',
        'form_config.py'
    )
    
    with open(config_path, 'r') as f:
        content = f.read()
    
    # Replace VERTICAL_OFFSET value
    import re
    content = re.sub(
        r'VERTICAL_OFFSET = \d+',
        f'VERTICAL_OFFSET = {offset_value}',
        content
    )
    
    with open(config_path, 'w') as f:
        f.write(content)
    
    # Reload modules
    reload_config()
    importlib.reload(sys.modules['print_handler.pdf_filler.form_filler'])
    
    # Generate PDF
    from print_handler.pdf_filler.form_filler import TransactionFormFiller
    form_filler = TransactionFormFiller()
    filled_pdf = form_filler.fill_transaction_form(transaction)
    
    # Save with offset in filename
    output_dir = os.path.join(settings.MEDIA_ROOT, 'transaction_forms', 'test_adjustments')
    os.makedirs(output_dir, exist_ok=True)
    
    filename = f"test_offset_{offset_value}pts.pdf"
    output_path = os.path.join(output_dir, filename)
    
    with open(output_path, 'wb') as f:
        f.write(filled_pdf.read())
    
    return output_path

def main():
    print("\n" + "="*80)
    print("  PDF POSITION ADJUSTMENT TOOL")
    print("="*80)
    
    # Get most recent transaction
    transaction = Transaction.objects.filter(action='Take').order_by('-date_time').first()
    
    if not transaction:
        print("\n✗ No transactions found")
        print("Create a withdrawal transaction first")
        return False
    
    print(f"\n✓ Using Transaction #{transaction.id}")
    print(f"  Personnel: {transaction.personnel.get_full_name()}")
    print(f"  Item: {transaction.item.item_type} {transaction.item.serial}")
    
    print("\n" + "="*80)
    print("  ADJUSTMENT GUIDE")
    print("="*80)
    print("\nVERTICAL_OFFSET moves ALL text up or down:")
    print("  • 0 points   = Original position")
    print("  • 18 points  = 0.25 inch down")
    print("  • 36 points  = 0.5 inch down  ⭐ RECOMMENDED START")
    print("  • 54 points  = 0.75 inch down")
    print("  • 72 points  = 1 inch down")
    print("\nRemember: 72 points = 1 inch")
    
    print("\n" + "="*80)
    print("  GENERATE TEST PDFs")
    print("="*80)
    
    # Generate test PDFs with different offsets
    test_offsets = [0, 18, 36, 54, 72]
    
    print("\nGenerating test PDFs with different offsets...")
    generated = []
    
    for offset in test_offsets:
        print(f"\n  Generating with offset = {offset} points ({offset/72:.2f}\")...", end=" ")
        try:
            path = generate_test_pdf(offset, transaction)
            print("✓")
            generated.append((offset, path))
        except Exception as e:
            print(f"✗ Error: {str(e)}")
    
    if not generated:
        print("\n✗ No PDFs generated")
        return False
    
    print("\n" + "="*80)
    print("  TEST PDFs GENERATED")
    print("="*80)
    
    output_dir = os.path.dirname(generated[0][1])
    print(f"\n📁 Location: {output_dir}")
    
    print("\n📄 Generated files:")
    for offset, path in generated:
        filename = os.path.basename(path)
        print(f"  • {filename} (shift down {offset/72:.2f}\")")
    
    print("\n" + "="*80)
    print("  NEXT STEPS")
    print("="*80)
    
    print("\n1. Print each test PDF to see which looks best:")
    print(f"   {output_dir}")
    
    print("\n2. Compare the printed forms:")
    print("   • Check if header 'PHILIPPINE AIR FORCE' is visible")
    print("   • Check if all text fields align properly")
    print("   • Check if signatures appear at bottom")
    
    print("\n3. Find the best offset value (likely 36 or 54)")
    
    print("\n4. Update the configuration:")
    print("   • Open: print_handler/pdf_filler/form_config.py")
    print("   • Change: VERTICAL_OFFSET = 36  (or your chosen value)")
    print("   • Save the file")
    
    print("\n5. Test with real transaction:")
    print("   python test_print_now.py")
    
    print("\n💡 TIPS:")
    print("   • If top still cut: increase VERTICAL_OFFSET")
    print("   • If bottom cut off: decrease VERTICAL_OFFSET")
    print("   • If text doesn't align: adjust individual fields in config")
    
    print("\n" + "="*80)
    print("\n✅ Test PDFs ready for printing comparison!")
    print(f"   Open folder: {output_dir}")
    print("="*80 + "\n")
    
    # Open the output directory
    try:
        os.startfile(output_dir)
        print("📂 Folder opened in File Explorer")
    except:
        pass
    
    return True

if __name__ == '__main__':
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠ Cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
