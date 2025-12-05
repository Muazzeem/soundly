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



