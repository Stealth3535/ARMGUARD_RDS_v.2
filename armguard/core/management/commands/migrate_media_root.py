"""
Management command: migrate_media_root

Copies all media files from a legacy MEDIA_ROOT path into the current
MEDIA_ROOT (settings.MEDIA_ROOT), preserving sub-directory structure.

Background
----------
When the server previously ran with MEDIA_ROOT = BASE_DIR / 'media'
(wrong path), all uploaded files (profile photos, QR images, etc.) were
stored at armguard/media/.  After the fix to BASE_DIR / 'core' / 'media',
Django now resolves file paths to armguard/core/media/ — so every
`os.path.exists(personnel.picture.path)` call returns False even though
the file is physically present, just in the wrong directory.

This command:
  1. Finds every file under OLD_ROOT that does NOT exist under NEW_ROOT
  2. Copies it, preserving the relative path
  3. Prints a summary

Usage
-----
  python manage.py migrate_media_root
  python manage.py migrate_media_root --old /path/to/old/media
  python manage.py migrate_media_root --dry-run          # preview only
  python manage.py migrate_media_root --delete-old       # remove originals after copy
"""
import os
import shutil
from pathlib import Path

from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = (
        "Copy media files from a legacy MEDIA_ROOT into the current "
        "settings.MEDIA_ROOT, preserving sub-directory structure."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--old",
            dest="old_root",
            default=None,
            help=(
                "Path to the old / legacy MEDIA_ROOT.  "
                "Defaults to BASE_DIR / 'media' (the previously wrong path)."
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would be copied without actually copying.",
        )
        parser.add_argument(
            "--delete-old",
            action="store_true",
            help="Delete the source file after a successful copy.",
        )

    def handle(self, *args, **options):
        from django.conf import settings

        new_root = Path(settings.MEDIA_ROOT)
        old_root = Path(options["old_root"]) if options["old_root"] else (
            # Default: BASE_DIR / 'media'  (the previously wrong value)
            Path(settings.BASE_DIR) / "media"
        )

        dry_run    = options["dry_run"]
        delete_old = options["delete_old"]

        self.stdout.write(self.style.HTTP_INFO(
            f"\n{'[DRY RUN] ' if dry_run else ''}Media migration\n"
            f"  OLD root : {old_root}\n"
            f"  NEW root : {new_root}\n"
        ))

        if not old_root.is_dir():
            self.stdout.write(self.style.WARNING(
                f"Old root does not exist: {old_root}\n"
                "Nothing to migrate."
            ))
            return

        copied  = 0
        skipped = 0
        errors  = []

        for src in sorted(old_root.rglob("*")):
            if not src.is_file():
                continue

            rel      = src.relative_to(old_root)
            dst      = new_root / rel

            if dst.exists():
                skipped += 1
                self.stdout.write(f"  SKIP  {rel}  (already exists at destination)")
                continue

            if dry_run:
                self.stdout.write(f"  WOULD COPY  {rel}")
                copied += 1
                continue

            try:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                copied += 1
                self.stdout.write(self.style.SUCCESS(f"  COPIED  {rel}"))

                if delete_old:
                    src.unlink()
                    self.stdout.write(f"           deleted source: {src}")

            except Exception as exc:
                errors.append((str(rel), str(exc)))
                self.stdout.write(self.style.ERROR(f"  ERROR   {rel}  — {exc}"))

        # Summary
        self.stdout.write("\n" + ("=" * 60))
        if dry_run:
            self.stdout.write(self.style.WARNING(
                f"[DRY RUN] Would copy: {copied}  |  Already exist: {skipped}"
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"Done.  Copied: {copied}  |  Skipped (already existed): {skipped}"
                + (f"  |  Errors: {len(errors)}" if errors else "")
            ))

        if errors:
            self.stdout.write(self.style.ERROR("\nErrors:"))
            for rel, exc in errors:
                self.stdout.write(self.style.ERROR(f"  {rel}: {exc}"))

        if not dry_run and copied > 0:
            self.stdout.write(self.style.HTTP_INFO(
                "\nNext step — regenerate ID cards with the migrated photos:\n"
                "  python manage.py generate_id_cards --force "
                "--settings=core.settings_production\n"
            ))
