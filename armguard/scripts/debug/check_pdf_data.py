import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from transactions.models import Transaction
from print_handler.pdf_filler.form_filler import TransactionFormFiller

t = Transaction.objects.get(id=10)
ff = TransactionFormFiller()
data = ff._prepare_data(t)

print(f"personnel_serial: {data['personnel_serial']}")
print(f"personnel_full: {data['personnel_full']}")
