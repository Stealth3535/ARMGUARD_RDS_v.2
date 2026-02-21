"""
ARMGUARD Device Authorization Middleware — v2
=============================================
A thin adapter that delegates all logic to DeviceService.
Middleware is now purely HTTP plumbing; security policy lives in the service layer.

Replace (in settings.py MIDDLEWARE list):
    'core.middleware.device_authorization.DeviceAuthorizationMiddleware'
with:
    'core.device.middleware.DeviceAuthMiddleware'
"""

import logging

from django.conf import settings
from django.http import HttpResponseRedirect, JsonResponse
from django.utils.deprecation import MiddlewareMixin

from .service import device_service
from .toggle import is_device_auth_enabled

logger = logging.getLogger('armguard.device.middleware')

# Redirect target for web browsers when unauthorized
UNAUTHORIZED_REDIRECT = '/admin/device/request-authorization/'


class DeviceAuthMiddleware(MiddlewareMixin):
    """
    Thin middleware adapter.

    Responsibilities:
      1. Call device_service.authorize_request(request)
      2. If denied: return 403 (API) or redirect (browser)
      3. If a new device token was issued: attach cookie on response
      4. Attach decision context to request for downstream views
    """

    def process_request(self, request):
        # Global on/off switch — controlled via Admin Settings or flag file
        if not is_device_auth_enabled():
            from .service import AuthDecision
            request.device_decision = AuthDecision(allowed=True, reason='device_auth_disabled')
            return None

        decision = device_service.authorize_request(request)

        # Attach for downstream use (views, templates, logging)
        request.device_decision = decision

        if decision.allowed:
            return None  # continue processing

        path = request.path
        logger.warning(
            'Device access DENIED | reason=%s device=%s ip=%s path=%s user=%s',
            decision.reason,
            getattr(decision.device, 'device_name', 'unknown'),
            device_service.identity.get_client_ip(request),
            path,
            getattr(getattr(request, 'user', None), 'username', 'anonymous'),
        )

        # API requests get JSON 403
        if path.startswith('/api/') or request.META.get('HTTP_ACCEPT', '').startswith('application/json'):
            return JsonResponse(
                {
                    'error': 'Device not authorized',
                    'code': 'DEVICE_NOT_AUTHORIZED',
                    'reason': decision.reason,
                    'security_level': decision.security_tier,
                    'message': (
                        'This device is not authorized for this operation. '
                        'Contact your administrator.'
                    ),
                },
                status=403,
            )

        # Browser: redirect to enrollment/request page
        return HttpResponseRedirect(UNAUTHORIZED_REDIRECT)

    def process_response(self, request, response):
        """
        If a new device token was generated during this request,
        set it as a cookie on the outbound response so the client
        carries it on all future requests.
        """
        decision = getattr(request, 'device_decision', None)
        if decision and getattr(decision, '_new_token', None):
            device_service.attach_token_cookie(response, decision._new_token)
        return response
