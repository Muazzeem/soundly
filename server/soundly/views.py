from django.http import JsonResponse
from django.views.decorators.http import require_http_methods


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
        },
        "documentation": "Visit /api/ for API endpoints",
    })



