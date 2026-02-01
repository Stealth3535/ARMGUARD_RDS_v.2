"""
Web Auto-Print Test - Opens browser and simulates transaction submission
This helps test the actual auto-print flow from the web interface
"""
import os
import sys
import django
import webbrowser
import time

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from transactions.models import Transaction
from personnel.models import Personnel
from inventory.models import Item

def print_section(title):
    print(f"\n{'='*80}")
    print(f"  {title}")
    print('='*80)

def main():
    print_section("WEB AUTO-PRINT TEST")
    
    print("\nThis test will help you verify the auto-print functionality")
    print("by guiding you through a live transaction on the web interface.")
    
    # Get test data
    personnel = Personnel.objects.filter(deleted_at__isnull=True).first()
    available_item = Item.objects.filter(status='Available').first()
    
    if not personnel:
        print("\n✗ No personnel found in database")
        return False
    
    if not available_item:
        print("\n✗ No available items found")
        print("   Return an item first to make one available")
        return False
    
    print(f"\n✓ Test Personnel: {personnel.get_full_name()} (ID: {personnel.id})")
    print(f"✓ Available Item: {available_item.item_type} {available_item.serial} (ID: {available_item.id})")
    
    print_section("TEST INSTRUCTIONS")
    
    print("\n📋 Step-by-Step Test Procedure:")
    print("\n1. Browser will open to transactions page")
    print("2. Open browser console (F12 → Console tab)")
    print("3. Enter the following details:")
    print(f"   • Personnel ID: {personnel.id}")
    print(f"   • Item ID: {available_item.id}")
    print(f"   • Action: Withdraw")
    print(f"   • Duty Type: (your choice)")
    print(f"   • Mags/Rounds: (optional)")
    print("\n4. Click 'Submit Transaction'")
    print("\n5. Watch for console messages:")
    print("   ✓ 'Auto-print triggered for transaction XX'")
    print("   ✓ 'PDF loaded, triggering print...'")
    print("   ✓ 'Print triggered successfully'")
    print("\n6. Print dialog should appear")
    print("   • Select EPSON L3210 Series")
    print("   • Paper size: Legal (8.5\" x 14\")")
    print("   • Click 'Print'")
    print("\n7. Page reloads after 2 seconds")
    print("\n8. Check your EPSON L3210 for printed form")
    
    print_section("BROWSER CONSOLE COMMANDS")
    
    print("\nUseful console commands to check auto-print status:")
    print("\n// Check if iframe was created")
    print("document.querySelectorAll('iframe').length")
    print("\n// Check console logs")
    print("// Look for the Auto-print messages above")
    
    print_section("TROUBLESHOOTING")
    
    print("\n❌ If print dialog doesn't appear:")
    print("   1. Check console for errors")
    print("   2. Disable popup blockers")
    print("   3. Ensure JavaScript enabled")
    print("   4. Check network tab for PDF request")
    print("\n❌ If dialog appears but no printer:")
    print("   1. Set EPSON L3210 as default printer")
    print("   2. Check printer power and connection")
    print("   3. Verify printer drivers installed")
    print("\n❌ If page reloads too fast:")
    print("   1. Check if you selected 'Withdraw' (not 'Return')")
    print("   2. This was fixed - should wait 2 seconds now")
    
    response = input("\n⚠ Press ENTER to open browser, or Ctrl+C to cancel: ")
    
    # Open browser
    url = "http://192.168.59.138:8000/transactions/"
    print(f"\n🌐 Opening: {url}")
    
    try:
        webbrowser.open(url)
        print("✓ Browser opened")
        print("\n⏳ Follow the test procedure above...")
        print("   Transaction page should be visible in your browser")
        
        # Get the most recent transaction for reference
        print("\n" + "="*80)
        print("  RECENT TRANSACTIONS (for reference)")
        print("="*80)
        
        recent = Transaction.objects.order_by('-date_time')[:3]
        for trans in recent:
            print(f"\nTransaction #{trans.id}")
            print(f"  Personnel: {trans.personnel.get_full_name()}")
            print(f"  Item: {trans.item.item_type} {trans.item.serial}")
            print(f"  Action: {trans.action}")
            print(f"  Date: {trans.date_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        print("\n" + "="*80)
        print("\n💡 After completing the test transaction:")
        print("   • Check if PDF printed to EPSON L3210")
        print("   • Verify form has correct data")
        print("   • Confirm paper size is Legal (8.5\" x 14\")")
        print("\n📁 PDF saved to:")
        print("   core/media/transaction_forms/Transaction_XX_YYYYMMDD_HHMMSS.pdf")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Failed to open browser: {str(e)}")
        print(f"\n💡 Manual URL: {url}")
        return False

if __name__ == '__main__':
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠ Test cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
