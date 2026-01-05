"""
Common decorators for API views with error handling and logging
"""
import logging
from functools import wraps
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings

logger = logging.getLogger(__name__)


def handle_api_errors(view_func):
    """
    Decorator to handle exceptions in API views and return proper error responses
    Works with both function-based views (request as first arg) and method-based views (self, request)
    """
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        # Determine if this is a method (self, request) or function (request)
        request = None
        if args:
            # Check if first arg is request (has 'method' attribute) or self
            if hasattr(args[0], 'method'):
                request = args[0]
            elif len(args) > 1 and hasattr(args[1], 'method'):
                request = args[1]
        
        try:
            return view_func(*args, **kwargs)
        except Exception as e:
            user_info = 'unknown'
            path_info = 'unknown'
            method_info = 'unknown'
            
            if request:
                if hasattr(request, 'user'):
                    user_info = request.user.email if request.user.is_authenticated else 'anonymous'
                if hasattr(request, 'path'):
                    path_info = request.path
                if hasattr(request, 'method'):
                    method_info = request.method
            
            logger.error(
                f"Error in {view_func.__name__}: {str(e)}",
                exc_info=True,
                extra={
                    'user': user_info,
                    'path': path_info,
                    'method': method_info,
                }
            )
            
            # Return appropriate error response
            error_detail = str(e) if settings.DEBUG else 'An error occurred. Please try again later.'
            return Response(
                {'error': error_detail},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    return wrapper


def validate_uuid(param_name='id'):
    """
    Decorator to validate UUID parameters in URL
    Works with both function-based and method-based views
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(*args, **kwargs):
            uuid_value = kwargs.get(param_name)
            if uuid_value:
                try:
                    import uuid
                    uuid.UUID(str(uuid_value))
                except (ValueError, TypeError):
                    logger.warning(f"Invalid UUID format for {param_name}: {uuid_value}")
                    return Response(
                        {'error': f'Invalid {param_name} format'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            return view_func(*args, **kwargs)
        return wrapper
    return decorator
