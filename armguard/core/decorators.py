"""
Core decorators for ARMGUARD application
Includes error handling, caching, and audit decorators
"""
import functools
import logging
from django.contrib import messages
from django.shortcuts import redirect
from django.db import IntegrityError, transaction
from django.core.exceptions import ValidationError, PermissionDenied
from django.http import Http404, HttpResponseServerError
from django.urls import reverse

logger = logging.getLogger(__name__)


def handle_database_errors(redirect_url=None, error_message=None):
    """
    Decorator to standardize error handling across views.
    
    Handles:
    - ValidationError: Shows user-friendly validation messages
    - IntegrityError: Database constraint violations
    - PermissionDenied: Access control violations  
    - Http404: Not found errors
    - General exceptions: Logs and shows generic message
    
    Usage:
        @handle_database_errors(redirect_url='admin:dashboard', error_message='Operation failed')
        def my_view(request):
            # Your view code
    """
    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapper(request, *args, **kwargs):
            try:
                return view_func(request, *args, **kwargs)
                
            except ValidationError as e:
                # Field validation errors
                if hasattr(e, 'message_dict'):
                    for field, errors in e.message_dict.items():
                        for error in errors:
                            messages.error(request, f"{field}: {error}")
                elif hasattr(e, 'messages'):
                    for error in e.messages:
                        messages.error(request, str(error))
                else:
                    messages.error(request, str(e))
                
                logger.warning(f"Validation error in {view_func.__name__}: {e}")
                
                if redirect_url:
                    return redirect(redirect_url)
                return redirect(request.META.get('HTTP_REFERER', '/'))
                
            except IntegrityError as e:
                # Database constraint violations
                error_msg = error_message or "Database integrity error occurred. This might be due to duplicate data or violated constraints."
                messages.error(request, error_msg)
                logger.error(f"Integrity error in {view_func.__name__}: {e}", exc_info=True)
                
                if redirect_url:
                    return redirect(redirect_url)
                return redirect(request.META.get('HTTP_REFERER', '/'))
                
            except PermissionDenied as e:
                # Permission/authorization errors
                messages.error(request, "You do not have permission to perform this action.")
                logger.warning(f"Permission denied in {view_func.__name__} for user {request.user}: {e}")
                return redirect('login')
                
            except Http404 as e:
                # Not found error
                messages.error(request, "The requested resource was not found.")
                logger.warning(f"404 error in {view_func.__name__}: {e}")
                
                if redirect_url:
                    return redirect(redirect_url)
                return redirect('armguard_admin:dashboard')
                
            except Exception as e:
                # Catch-all for unexpected errors
                error_msg = error_message or "An unexpected error occurred. Please try again or contact support."
                messages.error(request, error_msg)
                logger.exception(f"Unexpected error in {view_func.__name__}: {e}")
                
                if redirect_url:
                    return redirect(redirect_url)
                return redirect('armguard_admin:dashboard')
                
        return wrapper
    return decorator


def atomic_transaction(view_func):
    """
    Decorator to wrap view in atomic transaction with error handling.
    
    Ensures all database operations succeed or all fail together.
    Automatically rolls back on any exception.
    
    Usage:
        @atomic_transaction
        def my_view(request):
            # All DB operations here are atomic
    """
    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        try:
            with transaction.atomic():
                return view_func(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Transaction failed in {view_func.__name__}: {e}", exc_info=True)
            raise
    return wrapper


def with_audit_context(view_func):
    """
    Decorator to automatically set audit context on request object.
    
    Adds audit_context attribute to request with:
    - user: Authenticated user
    - ip: Client IP address
    - user_agent: Browser user agent
    - session: Session key
    
    Usage:
        @with_audit_context
        def my_view(request):
            audit_context = request.audit_context
            personnel.set_audit_context(request)
    """
    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        request.audit_context = {
            'user': request.user if request.user.is_authenticated else None,
            'ip': request.META.get('REMOTE_ADDR'),
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'session': request.session.session_key if hasattr(request, 'session') else None
        }
        return view_func(request, *args, **kwargs)
    return wrapper


def require_ajax(view_func):
    """
    Decorator to ensure view is only accessed via AJAX.
    
    Returns 400 Bad Request if not an AJAX request.
    """
    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            messages.error(request, "This endpoint requires an AJAX request.")
            return redirect('armguard_admin:dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


# Combine decorators for common patterns
def safe_database_operation(redirect_url='armguard_admin:dashboard'):
    """
    Combined decorator for safe database operations.
    Applies atomic transaction + error handling.
    
    Usage:
        @safe_database_operation(redirect_url='admin:user_management')
        def delete_user(request, user_id):
            # Safe atomic operation with error handling
    """
    def decorator(view_func):
        @with_audit_context
        @handle_database_errors(redirect_url=redirect_url)
        @atomic_transaction
        @functools.wraps(view_func)
        def wrapper(request, *args, **kwargs):
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
