"""
Regenerate a transaction's PDF with current settings
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from transactions.models import Transaction
from print_handler.pdf_filler.form_filler import TransactionFormFiller
from django.conf import settings

# Get transaction 18
t = Transaction.objects.get(id=18)
print(f"Regenerating PDF for Transaction #{t.id}")
print(f"Personnel: {t.personnel.firstname} {t.personnel.surname}")
print(f"Item: {t.item.item_type} {t.item.serial}")

# Generate PDF
filler = TransactionFormFiller()
pdf = filler.fill_transaction_form(t)

# Save it
filename = f"Transaction_{t.id}_SHIFTED.pdf"
output_path = os.path.join(settings.MEDIA_ROOT, 'transaction_forms', filename)

with open(output_path, 'wb') as f:
    f.write(pdf.read())

print(f"✓ Saved to: {output_path}")
print(f"File size: {os.path.getsize(output_path):,} bytes")
