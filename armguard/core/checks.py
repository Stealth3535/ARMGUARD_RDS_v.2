"""
Django system checks for ArmGuard.

These run automatically when Django starts (manage.py runserver/gunicorn launch).
A W-level warning is issued if MEDIA_ROOT is not writable; an E-level error if
the directory cannot be created at all.

Register with:  CoreConfig.ready() → checks.register_all_checks()
"""
import os

from django.core.checks import Error, Warning, register


@register(deploy=False)   # runs on every startup, not just --deploy
def check_media_root(app_configs, **kwargs):
    """
    Verify MEDIA_ROOT exists and is writable.

    Common deployment failure: .env has an obsolete MEDIA_ROOT value that
    differs from the path the app was configured for, causing all file lookups
    to silently fail.
    """
    from django.conf import settings

    errors = []
    media_root = str(settings.MEDIA_ROOT)

    # 1. Directory must exist (settings.py tries to create it at import time;
    #    if it still does not exist then something is seriously wrong).
    if not os.path.isdir(media_root):
        errors.append(
            Error(
                f"MEDIA_ROOT directory does not exist: {media_root!r}",
                hint=(
                    "Check that your .env file does NOT define MEDIA_ROOT with a "
                    "wrong/old path.  The correct path is derived automatically as "
                    "BASE_DIR / 'core' / 'media'.  Remove the MEDIA_ROOT line from "
                    ".env unless you intentionally want to override the location."
                ),
                id="core.E001",
            )
        )
        return errors   # no point checking writability if dir is missing

    # 2. Directory must be writable.
    if not os.access(media_root, os.W_OK):
        errors.append(
            Warning(
                f"MEDIA_ROOT is not writable: {media_root!r}",
                hint=(
                    f"Run: sudo chown -R rds:rds {media_root!r}  "
                    "and ensure the gunicorn process user has write access."
                ),
                id="core.W001",
            )
        )

    # 3. Required sub-directories.
    required_subdirs = ('personnel_id_cards', 'transaction_forms')
    for subdir in required_subdirs:
        path = os.path.join(media_root, subdir)
        if not os.path.isdir(path):
            errors.append(
                Warning(
                    f"MEDIA_ROOT sub-directory missing: {path!r}",
                    hint=(
                        f"Run: mkdir -p {path!r}  "
                        "This directory is created automatically on startup when settings "
                        "are loaded; its absence means settings were not imported correctly."
                    ),
                    id="core.W002",
                )
            )

    return errors


def register_all_checks():
    """Called from CoreConfig.ready() to activate all system checks."""
    # The @register decorator already registered check_media_root above;
    # this function exists so CoreConfig.ready() has a single import point
    # and future checks can be added here without touching apps.py.
    pass  # registration is done at module import via @register decorator
