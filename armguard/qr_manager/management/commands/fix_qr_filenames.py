"""
Management command to fix QR image filenames that contain dots in the stem.
Dots confuse web servers (nginx/Apache treat them as extensions) causing 404s.

Also creates missing QR records for inventory items that don't have one.

Usage:
    python manage.py fix_qr_filenames
    python manage.py fix_qr_filenames --dry-run
"""
import os
from django.core.management.base import BaseCommand
from qr_manager.models import QRCodeImage


class Command(BaseCommand):
    help = 'Fix QR image filenames with dots in the stem, and create missing QR records for items'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be fixed without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN — no changes will be made\n'))

        fixed = 0
        skipped = 0
        errors = 0

        # ── 1. Fix existing records with dotted filename stems ───────────────
        self.stdout.write('--- Checking all QR records for dotted filenames ---')
        for qr in QRCodeImage.all_objects.all():
            if not qr.qr_image:
                continue
            stem = os.path.splitext(os.path.basename(qr.qr_image.name))[0]
            if '.' not in stem:
                skipped += 1
                continue

            self.stdout.write(
                self.style.WARNING(f'  DOTTED: {qr.reference_id}  →  {qr.qr_image.name}')
            )
            if dry_run:
                fixed += 1
                continue

            try:
                qr.qr_image.delete(save=False)
                qr.qr_image = None
                qr.generate_qr_code()
                qr.save()
                self.stdout.write(
                    self.style.SUCCESS(f'  FIXED : {qr.reference_id}  →  {qr.qr_image.name}')
                )
                fixed += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ERROR : {qr.reference_id} — {e}'))
                errors += 1

        # ── 2. Create missing QR records for inventory items ─────────────────
        self.stdout.write('\n--- Checking inventory items for missing QR records ---')
        try:
            from inventory.models import Item
            for item in Item.objects.all():
                exists = QRCodeImage.all_objects.filter(
                    qr_type=QRCodeImage.TYPE_ITEM,
                    reference_id=item.id,
                ).exists()
                if exists:
                    continue

                self.stdout.write(
                    self.style.WARNING(f'  MISSING QR: {item.id}')
                )
                if dry_run:
                    fixed += 1
                    continue

                try:
                    qr = QRCodeImage(
                        qr_type=QRCodeImage.TYPE_ITEM,
                        reference_id=item.id,
                        qr_data=item.id,
                        is_active=True,
                    )
                    qr.generate_qr_code()
                    qr.save()
                    self.stdout.write(
                        self.style.SUCCESS(f'  CREATED: {item.id}  →  {qr.qr_image.name}')
                    )
                    fixed += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'  ERROR : {item.id} — {e}'))
                    errors += 1
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Could not check inventory items: {e}'))

        self.stdout.write(
            self.style.SUCCESS(
                f'\nDone — fixed/created: {fixed}, unchanged: {skipped}, errors: {errors}'
            )
        )
