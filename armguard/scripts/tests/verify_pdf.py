"""Verify transaction PDF output"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from transactions.models import Transaction

t = Transaction.objects.order_by('-id').first()

print("=" * 80)
print("TRANSACTION DATA USED FOR PDF:")
print("=" * 80)
print(f"Transaction ID: #{t.id}")
print(f"Date: {t.date_time.strftime('%d/%m/%Y')}")
print(f"Time: {t.date_time.strftime('%H:%M:%S')}")
print()
print("PERSONNEL INFORMATION:")
print(f"  Name: {t.personnel.get_full_name()}")
print(f"  Rank: {t.personnel.rank}")
print(f"  Serial (AFSN): {t.personnel.serial}")
print(f"  Unit/Office: {t.personnel.group}")
print(f"  Full Format: {t.personnel.rank} {t.personnel.firstname} {t.personnel.surname} {t.personnel.serial} PAF")
print()
print("ITEM INFORMATION:")
print(f"  Classification: {t.item.item_type}")
print(f"  Serial Number: {t.item.serial}")
print(f"  Condition: {t.item.condition}")
print()
print("TRANSACTION DETAILS:")
print(f"  Action: {t.action}")
print(f"  Magazines: {t.mags}")
print(f"  Rounds: {t.rounds}")
print(f"  Purpose/Duty: {t.duty_type or '(none)'}")
print(f"  Notes: {t.notes or '(none)'}")
print()
print("ISSUED BY:")
if t.issued_by:
    if hasattr(t.issued_by, 'personnel') and t.issued_by.personnel:
        issuer = t.issued_by.personnel
        print(f"  {issuer.rank} {issuer.firstname} {issuer.surname} {issuer.serial} PAF")
    else:
        print(f"  {t.issued_by.get_full_name() or t.issued_by.username} (no personnel record)")
else:
    print("  N/A")
print("=" * 80)
print()
print("Expected PDF should show:")
print("- Top form and bottom form both filled with same data")
print("- Date in top right corner")
print("- Complete name, rank, AFSN, office on first line")
print("- Items classification, mags, rounds on second line")
print("- Serial number of item")
print("- Purpose field")
print("- 'Received By' signature with personnel full name + PAF")
print("- 'Issued By' signature with armorer full name + PAF")
print("- Small transaction ID and time in top right")
print()
print("Check the PDF at: core/media/transaction_forms/test_output.pdf")
