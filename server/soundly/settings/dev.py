from .base import *

DEBUG = True

SECRET_KEY = config("SECRET_KEY")

# Allow all hosts in development for convenience
ALLOWED_HOSTS = ["*"]

# CSRF trusted origins for development
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:8080",
    "http://localhost:5173",
    "http://127.0.0.1:8000",
    "http://127.0.0.1:8080",
    "http://localhost:3000",
]

# CORS - For development, explicitly allow localhost origins
# Custom middleware handles CORS headers
CORS_ALLOW_ALL_ORIGINS = True  # Allow all in dev for simplicity
CORS_ALLOW_CREDENTIALS = False  # Must be False when ALLOW_ALL_ORIGINS is True
CORS_ALLOWED_ORIGINS = [
    "http://localhost:8080",
    "http://localhost:5173",
    "http://127.0.0.1:8000",
    "http://127.0.0.1:8080",
    "http://localhost:3000",  # Common React dev port
]
# Ensure CORS handles preflight requests
CORS_PREFLIGHT_MAX_AGE = 86400
# Allow all methods and headers for development
CORS_ALLOW_METHODS = [
    "DELETE",
    "GET",
    "OPTIONS",
    "PATCH",
    "POST",
    "PUT",
]
CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]

# JWT settings for development (less strict)
REST_AUTH["JWT_AUTH_SECURE"] = False  # Allow HTTP in dev
REST_AUTH["JWT_AUTH_HTTPONLY"] = True  # Still use HTTPONLY for security

# Email configuration for development
# Use console backend to print emails to console (easier for testing)
EMAIL_BACKEND = config("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")

# If you want to use SMTP, configure these in .env:
# EMAIL_HOST = config("EMAIL_HOST", default="")
# EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
# EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)
# EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
# EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
# DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="noreply@example.com")

try:
    from .local import *
except ImportError:
    pass
