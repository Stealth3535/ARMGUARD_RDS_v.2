# core/models.py
# Re-export all device models so Django's migration framework discovers them
# under the 'core' app label.

from core.device.models import (  # noqa: F401
    AuthorizedDevice,
    DeviceAuditEvent,
    DeviceMFAChallenge,
    DeviceAccessLog,
    DeviceRiskEvent,
)
