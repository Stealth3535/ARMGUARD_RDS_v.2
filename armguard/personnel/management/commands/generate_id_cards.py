"""
Management command: generate_id_cards
Usage:
    python manage.py generate_id_cards            # all active personnel
    python manage.py generate_id_cards --all      # include soft-deleted
    python manage.py generate_id_cards --force    # regenerate even if file exists
    python manage.py generate_id_cards --id PO-154068180226  # single personnel
"""
import os
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = "Generate PNG ID cards for all personnel and save to core/media/personnel_id_cards/"

    def add_arguments(self, parser):
        parser.add_argument(
            "--all",
            action="store_true",
            dest="include_deleted",
            help="Include soft-deleted personnel (default: active only)",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Regenerate cards even if the file already exists",
        )
        parser.add_argument(
            "--id",
            dest="personnel_id",
            default=None,
            help="Generate card for a single personnel ID only",
        )

    def handle(self, *args, **options):
        from personnel.models import Personnel
        from utils.personnel_id_card_generator import generate_personnel_id_card

        out_dir = os.path.join(settings.MEDIA_ROOT, "personnel_id_cards")
        os.makedirs(out_dir, exist_ok=True)

        force          = options["force"]
        include_deleted = options["include_deleted"]
        single_id      = options.get("personnel_id")

        # Build queryset
        if single_id:
            qs = Personnel.all_objects.filter(id=single_id)
        elif include_deleted:
            qs = Personnel.all_objects.all()
        else:
            qs = Personnel.objects.all()   # active only (soft-delete filtered)

        total   = qs.count()
        skipped = 0
        success = 0
        failed  = 0

        self.stdout.write(self.style.HTTP_INFO(
            f"Generating ID cards for {total} personnel -> {out_dir}"
        ))

        for idx, person in enumerate(qs.iterator(), 1):
            combined_path = os.path.join(out_dir, f"{person.id}.png")

            if not force and os.path.exists(combined_path):
                skipped += 1
                self.stdout.write(f"  [{idx}/{total}] SKIP  {person.id}  (already exists)")
                continue

            try:
                generate_personnel_id_card(person)
                success += 1
                self.stdout.write(
                    self.style.SUCCESS(f"  [{idx}/{total}] OK    {person.id}  {person.rank or ''} {person.get_full_name()}")
                )
            except Exception as exc:
                failed += 1
                self.stdout.write(
                    self.style.ERROR(f"  [{idx}/{total}] FAIL  {person.id}  — {exc}")
                )

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"Done - {success} generated, {skipped} skipped, {failed} failed  (total {total})"
        ))
