"""
Management command to audit and repair all QR codes:
  1. Fix dotted filename stems (confuse nginx/Apache → 404)
  2. Regenerate missing files (DB record exists but file absent on disk)
  3. Create missing DB records for inventory items that have none

Usage:
    python manage.py fix_qr_filenames
    python manage.py fix_qr_filenames --dry-run
"""
import os
from django.conf import settings
from django.core.management.base import BaseCommand
from qr_manager.models import QRCodeImage


def _file_exists(qr):
    """Return True if the physical media file exists on disk."""
    if not qr.qr_image:
        return False
    full_path = os.path.join(settings.MEDIA_ROOT, qr.qr_image.name)
    return os.path.exists(full_path)


class Command(BaseCommand):
    help = 'Audit and repair QR images: fix dotted filenames, regenerate missing files, create missing records'

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

        # ── 1. Check all existing QR records ─────────────────────────────────
        self.stdout.write('--- Auditing existing QR records ---')
        self.stdout.write(f'  MEDIA_ROOT: {settings.MEDIA_ROOT}')
        for qr in QRCodeImage.all_objects.all():
            needs_regen = False
            reason = ''

            if not qr.qr_image:
                needs_regen = True
                reason = 'NO IMAGE FIELD'
            else:
                stem = os.path.splitext(os.path.basename(qr.qr_image.name))[0]
                if '.' in stem:
                    needs_regen = True
                    reason = f'DOTTED STEM ({qr.qr_image.name})'
                elif not _file_exists(qr):
                    needs_regen = True
                    reason = f'FILE MISSING ({qr.qr_image.name})'

            if not needs_regen:
                skipped += 1
                continue

            self.stdout.write(
                self.style.WARNING(f'  {reason}: {qr.reference_id}')
            )
            if dry_run:
                fixed += 1
                continue

            try:
                if qr.qr_image:
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

        # ── 2. Create missing DB records for inventory items ──────────────────
        self.stdout.write('\n--- Checking inventory items for missing QR records ---')
        try:
            from inventory.models import Item
            for item in Item.objects.all():
                has_record = QRCodeImage.all_objects.filter(
                    qr_type=QRCodeImage.TYPE_ITEM,
                    reference_id=item.id,
                ).exists()
                if has_record:
                    continue

                self.stdout.write(
                    self.style.WARNING(f'  MISSING RECORD: {item.id}')
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
