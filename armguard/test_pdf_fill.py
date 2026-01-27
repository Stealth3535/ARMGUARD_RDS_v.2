"""Test PDF form filling"""
import os
import django

# Setup Django FIRST
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from print_handler.pdf_filler.form_filler import TransactionFormFiller
from transactions.models import Transaction

# Test
t = Transaction.objects.order_by('-id').first()
print(f'Testing transaction {t.id}')

filler = TransactionFormFiller()
info = filler.get_page_info()
print(f'PDF page info: {info}')

pdf = filler.fill_transaction_form(t)

output_path = r'c:\Users\9533RDS\Desktop\Armguard\armguard\core\media\transaction_forms\test_output.pdf'
os.makedirs(os.path.dirname(output_path), exist_ok=True)

with open(output_path, 'wb') as f:
    f.write(pdf.read())

print(f'✓ Saved to: {output_path}')
print(f'File size: {os.path.getsize(output_path)} bytes')
