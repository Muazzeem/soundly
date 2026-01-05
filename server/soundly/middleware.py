"""
Custom CORS middleware that adds CORS headers to all responses.
This ensures CORS works properly for frontend-backend communication.
"""
from django.http import HttpResponse
from django.conf import settings


class CustomCorsMiddleware:
    """
    Middleware that adds CORS headers to every response.
    In development, allows all origins. In production, should be configured
    to only allow specific origins.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Handle OPTIONS preflight requests
        if request.method == "OPTIONS":
            response = HttpResponse()
            self._add_cors_headers(request, response)
            return response
        
        # Process the request
        response = self.get_response(request)
        
        # Add CORS headers to the response
        self._add_cors_headers(request, response)
        
        return response
    
    def _add_cors_headers(self, request, response):
        """Add CORS headers based on settings."""
        origin = request.META.get("HTTP_ORIGIN", "")
        
        # In development, allow all origins
        # In production, this should check CORS_ALLOWED_ORIGINS
        allow_all = getattr(settings, "CORS_ALLOW_ALL_ORIGINS", False) or settings.DEBUG
        
        if allow_all:
            response["Access-Control-Allow-Origin"] = "*"
        else:
            # Check if origin is in allowed origins
            allowed_origins = getattr(settings, "CORS_ALLOWED_ORIGINS", [])
            if origin in allowed_origins:
                response["Access-Control-Allow-Origin"] = origin
        
        # Add other CORS headers
        response["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-CSRFToken"
        
        # Handle credentials if needed
        if getattr(settings, "CORS_ALLOW_CREDENTIALS", False):
            response["Access-Control-Allow-Credentials"] = "true"
            # Can't use wildcard with credentials
            if response.get("Access-Control-Allow-Origin") == "*" and origin:
                response["Access-Control-Allow-Origin"] = origin
        
        # Preflight cache
        response["Access-Control-Max-Age"] = "86400"
