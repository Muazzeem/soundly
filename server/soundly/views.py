from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db import connection
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
def api_root(request):
    """
    Root endpoint that provides API information and available endpoints.
    """
    return JsonResponse({
        "name": "Soundly API",
        "version": "1.0",
        "description": "Music song exchange and matching API",
        "endpoints": {
            "api": "/api/",
            "admin": "/admin/",
            "authentication": {
                "signup": "/auth/signup/",
                "login": "/auth/login/",
                "logout": "/auth/logout/",
                "password_reset": "/password/reset/",
                "verify_otp": "/auth/verify-otp/",
                "resend_otp": "/auth/resend-otp/",
            },
            "search": "/search/",
            "health": "/health/",
            "ready": "/ready/",
        },
        "documentation": "Visit /api/ for API endpoints",
    })


@require_http_methods(["GET"])
def health_check(request):
    """
    Health check endpoint for load balancers and monitoring.
    Returns 200 if the application is running.
    """
    return JsonResponse({
        "status": "healthy",
        "service": "soundly-api",
    }, status=200)


@require_http_methods(["GET"])
def readiness_check(request):
    """
    Readiness check endpoint for Kubernetes and orchestration tools.
    Returns 200 if the application is ready to serve traffic.
    Checks database connectivity.
    """
    try:
        # Check database connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        
        return JsonResponse({
            "status": "ready",
            "service": "soundly-api",
            "checks": {
                "database": "ok",
            }
        }, status=200)
    except Exception as e:
        logger.error(f"Readiness check failed: {e}", exc_info=True)
        return JsonResponse({
            "status": "not_ready",
            "service": "soundly-api",
            "checks": {
                "database": "failed",
            },
            "error": str(e)
        }, status=503)


@require_http_methods(["GET", "OPTIONS"])
def cors_test(request):
    """
    Test endpoint to verify CORS is working.
    """
    from django.conf import settings
    
    data = {
        "message": "CORS test successful",
        "origin": request.META.get("HTTP_ORIGIN", "not provided"),
        "cors_settings": {
            "CORS_ALLOW_ALL_ORIGINS": getattr(settings, "CORS_ALLOW_ALL_ORIGINS", "NOT SET"),
            "CORS_ALLOWED_ORIGINS": getattr(settings, "CORS_ALLOWED_ORIGINS", "NOT SET"),
            "CORS_ALLOW_CREDENTIALS": getattr(settings, "CORS_ALLOW_CREDENTIALS", "NOT SET"),
            "cors_middleware_in_list": "corsheaders.middleware.CorsMiddleware" in settings.MIDDLEWARE,
            "custom_cors_middleware_in_list": "soundly.middleware.CustomCorsMiddleware" in settings.MIDDLEWARE,
            "cors_in_apps": "corsheaders" in settings.INSTALLED_APPS,
        }
    }
    
    response = JsonResponse(data)
    # CORS headers will be added by CustomCorsMiddleware
    # Log response headers for debugging
    if settings.DEBUG:
        cors_headers = {
            k: v for k, v in response.items() 
            if k.startswith("Access-Control-")
        }
        logger.debug(f"CORS test endpoint - Response headers: {list(cors_headers.keys())}")
    
    return response



