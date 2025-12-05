from .base import *

DEBUG = True

SECRET_KEY = config("SECRET_KEY")

# Allow all hosts in development for convenience
ALLOWED_HOSTS = ["*"]

# CORS - allow all in development
CORS_ALLOW_ALL_ORIGINS = True

# JWT settings for development (less strict)
REST_AUTH["JWT_AUTH_SECURE"] = False  # Allow HTTP in dev
REST_AUTH["JWT_AUTH_HTTPONLY"] = True  # Still use HTTPONLY for security

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

try:
    from .local import *
except ImportError:
    pass
