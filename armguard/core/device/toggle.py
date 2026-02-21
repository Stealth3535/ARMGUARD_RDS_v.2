"""
Device Authorization Toggle Utility
=====================================
Provides a single flag-file based on/off switch for the entire
device authorization system.

How it works
------------
* If  ``<BASE_DIR>/.device_auth_disabled``  exists  →  auth is OFF
* Otherwise                                          →  auth is ON  (default)

The flag file survives server restarts (unlike cache or in-process flags)
and requires no database migration.

The ``DEVICE_AUTH_ENABLED`` setting in settings.py (or .env) controls the
*initial* startup state:
  * ``DEVICE_AUTH_ENABLED=False`` in .env → creates the flag file on first
    import so the runtime check immediately returns False.
  * Omitted / True                        → flag file is NOT created.

Public API
----------
``is_device_auth_enabled()`` → bool
    Call this anywhere to check the current toggle state.

``set_device_auth_enabled(value: bool)``
    Creates or removes the flag file.  Call from the admin toggle view.
"""

import os

from django.conf import settings

# Absolute path to the flag file.
# BASE_DIR is always defined in core/settings.py.
_FLAG_FILE: str = os.path.join(str(settings.BASE_DIR), '.device_auth_disabled')


def is_device_auth_enabled() -> bool:
    """Return True if device authorization is currently active, False if disabled."""
    return not os.path.isfile(_FLAG_FILE)


def set_device_auth_enabled(value: bool) -> None:
    """
    Enable (value=True) or disable (value=False) device authorization.

    Creates / removes the flag file and optionally writes an audit note.
    """
    if value:
        # Enable: remove the flag file if it exists
        if os.path.isfile(_FLAG_FILE):
            os.remove(_FLAG_FILE)
    else:
        # Disable: create the flag file
        with open(_FLAG_FILE, 'w') as fh:
            fh.write(
                'Device authorization is DISABLED.\n'
                'Remove this file or use the Admin Settings toggle to re-enable.\n'
            )


# ── Honour DEVICE_AUTH_ENABLED from settings / .env at import time ────────────
# This lets operators set the initial state via environment without needing
# to touch the flag file manually.
_setting = getattr(settings, 'DEVICE_AUTH_ENABLED', True)
if not _setting and is_device_auth_enabled():
    # Setting says disabled but flag file doesn't exist yet → create it
    set_device_auth_enabled(False)
