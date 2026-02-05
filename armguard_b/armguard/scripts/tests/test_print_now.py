"""
Direct Print Test - Actually sends PDF to printer
This script will attempt to print the most recent transaction PDF to your default printer
"""
import os
import sys
import django
import subprocess
import platform

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from transactions.models import Transaction
from django.conf import settings
from print_handler.pdf_filler.form_filler import TransactionFormFiller

def print_section(title):
    """Print section header"""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print('='*80)

def print_pdf_windows(pdf_path):
    """Print PDF using Windows default printer"""
    try:
        # Method 1: Use Windows shell to print (sends to default printer)
        os.startfile(pdf_path, "print")
        return True, "Print job sent to default printer via Windows shell"
    except Exception as e:
        return False, f"Failed: {str(e)}"

def print_pdf_gsprint(pdf_path):
    """Print PDF using gsprint (if available)"""
    try:
        # Check if gsprint is available
        result = subprocess.run(['gsprint', '-query'], 
                              capture_output=True, 
                              timeout=5)
        if result.returncode == 0:
            # Send to default printer
            subprocess.run(['gsprint', '-printer', 'default', pdf_path], 
                          timeout=30)
            return True, "Printed via gsprint"
    except FileNotFoundError:
        return False, "gsprint not found"
    except Exception as e:
        return False, f"gsprint error: {str(e)}"

def print_pdf_sumatra(pdf_path):
    """Print PDF using SumatraPDF (if available)"""
    try:
        # Common SumatraPDF locations
        sumatra_paths = [
            r"C:\Program Files\SumatraPDF\SumatraPDF.exe",
            r"C:\Program Files (x86)\SumatraPDF\SumatraPDF.exe",
        ]
        
        for sumatra_path in sumatra_paths:
            if os.path.exists(sumatra_path):
                subprocess.run([sumatra_path, '-print-to-default', pdf_path], 
                             timeout=30)
                return True, f"Printed via SumatraPDF"
        
        return False, "SumatraPDF not found"
    except Exception as e:
        return False, f"SumatraPDF error: {str(e)}"

def main():
    print_section("DIRECT PRINT TEST")
    
    # Get the most recent Take transaction
    recent_take = Transaction.objects.filter(action='Take').order_by('-date_time').first()
    
    if not recent_take:
        print("✗ No Take transactions found in database")
        print("\n💡 Create a withdrawal transaction first:")
        print("   http://192.168.59.138:8000/transactions/")
        return False
    
    print(f"\n✓ Found Transaction: #{recent_take.id}")
    print(f"  Personnel: {recent_take.personnel.get_full_name()}")
    print(f"  Item: {recent_take.item.item_type} {recent_take.item.serial}")
    print(f"  Date/Time: {recent_take.date_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check if PDF exists, if not generate it
    date_str = recent_take.date_time.strftime('%Y%m%d_%H%M%S')
    filename = f"Transaction_{recent_take.id}_{date_str}.pdf"
    pdf_path = os.path.join(settings.MEDIA_ROOT, 'transaction_forms', filename)
    
    print_section("PDF FILE CHECK")
    
    if os.path.exists(pdf_path):
        file_size = os.path.getsize(pdf_path)
        print(f"✓ PDF exists: {filename}")
        print(f"✓ File size: {file_size:,} bytes")
        print(f"✓ Full path: {pdf_path}")
    else:
        print(f"✗ PDF not found, generating now...")
        try:
            form_filler = TransactionFormFiller()
            filled_pdf = form_filler.fill_transaction_form(recent_take)
            
            os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
            with open(pdf_path, 'wb') as f:
                f.write(filled_pdf.read())
            
            print(f"✓ PDF generated: {filename}")
            print(f"✓ Saved to: {pdf_path}")
        except Exception as e:
            print(f"✗ Failed to generate PDF: {str(e)}")
            return False
    
    print_section("PRINTER INFORMATION")
    
    if platform.system() == 'Windows':
        try:
            # List available printers using wmic
            result = subprocess.run(['wmic', 'printer', 'get', 'name'], 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=10)
            if result.returncode == 0:
                printers = [p.strip() for p in result.stdout.split('\n') if p.strip() and p.strip() != 'Name']
                if printers:
                    print("Available Printers:")
                    for printer in printers:
                        print(f"  • {printer}")
                        if 'EPSON L3210' in printer or 'L3210' in printer:
                            print(f"    ✓ EPSON L3210 FOUND")
                else:
                    print("⚠ No printers found")
            
            # Get default printer
            result = subprocess.run(['wmic', 'printer', 'where', 'default=true', 'get', 'name'], 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=10)
            if result.returncode == 0:
                default = result.stdout.split('\n')
                if len(default) > 1:
                    default_printer = default[1].strip()
                    if default_printer:
                        print(f"\n✓ Default Printer: {default_printer}")
                    else:
                        print(f"\n⚠ No default printer set")
        except Exception as e:
            print(f"⚠ Could not query printers: {str(e)}")
    
    print_section("ATTEMPTING TO PRINT")
    
    print("\nThis will send the PDF to your default printer...")
    print("Make sure:")
    print("  • EPSON L3210 is powered on")
    print("  • Legal size paper (8.5\" x 14\") is loaded")
    print("  • Printer is set as default in Windows")
    
    response = input("\n⚠ Press ENTER to print, or Ctrl+C to cancel: ")
    
    # Try different print methods
    success = False
    method_used = None
    
    # Method 1: Windows shell (most reliable)
    print("\n--- Method 1: Windows Shell Print ---")
    result, message = print_pdf_windows(pdf_path)
    print(message)
    if result:
        success = True
        method_used = "Windows Shell"
    
    # If Windows shell didn't work, try alternatives
    if not success:
        print("\n--- Method 2: SumatraPDF ---")
        result, message = print_pdf_sumatra(pdf_path)
        print(message)
        if result:
            success = True
            method_used = "SumatraPDF"
    
    if not success:
        print("\n--- Method 3: GSPrint ---")
        result, message = print_pdf_gsprint(pdf_path)
        print(message)
        if result:
            success = True
            method_used = "GSPrint"
    
    print_section("RESULT")
    
    if success:
        print(f"\n✅ PRINT JOB SENT SUCCESSFULLY!")
        print(f"   Method: {method_used}")
        print(f"   PDF: {filename}")
        print(f"\n📄 Check your EPSON L3210 printer")
        print(f"   The document should start printing shortly")
        print(f"\n💡 If nothing prints:")
        print(f"   1. Check printer power and connection")
        print(f"   2. Verify paper is loaded (Legal size)")
        print(f"   3. Check Windows print queue")
        print(f"   4. Try manual print: {pdf_path}")
    else:
        print(f"\n⚠ AUTOMATIC PRINT FAILED")
        print(f"\n💡 Manual Print Options:")
        print(f"   1. Open PDF manually: {pdf_path}")
        print(f"   2. Right-click → Print")
        print(f"   3. Or use your PDF reader (Adobe, Edge, Chrome)")
        print(f"\n💡 Web Print Option:")
        print(f"   http://192.168.59.138:8000/print/transaction/{recent_take.id}/pdf/")
    
    print("\n" + "="*80)
    return success

if __name__ == '__main__':
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠ Print cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
