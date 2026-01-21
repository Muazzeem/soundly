import os

from .base import *

DEBUG = True
SECRET_KEY = os.environ.get("SECRET_KEY", config("SECRET_KEY", default=""))
ALLOWED_HOSTS = ["*"]

CSRF_TRUSTED_ORIGINS = [
    "https://api.soundlybeats.com",
    "https://www.soundlybeats.com",
    "https://soundlybeats.com",
    "https://soundly-beats.vercel.app",
]

# CORS Configuration - restrict to specific origins in production
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    "https://api.soundlybeats.com",
    "https://www.soundlybeats.com",
    "https://soundlybeats.com",
    "https://soundly-beats.vercel.app",
]
CORS_ALLOW_CREDENTIALS = True

# JWT Security Settings for Production
REST_AUTH["JWT_AUTH_SECURE"] = True  # HTTPS only
REST_AUTH["JWT_AUTH_HTTPONLY"] = True  # Not accessible via JavaScript

# Security Headers
SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=False, cast=bool)
SECURE_HSTS_SECONDS = config("SECURE_HSTS_SECONDS", default=31536000, cast=int)  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

# Session Security
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

# Logging Configuration
# Ensure logs directory exists before configuring logging
logs_dir = os.path.join(BASE_DIR, "logs")
os.makedirs(logs_dir, exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(logs_dir, "django.log"),
            "maxBytes": 1024 * 1024 * 10,  # 10 MB
            "backupCount": 5,
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console", "file"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console", "file"],
            "level": config("DJANGO_LOG_LEVEL", default="INFO"),
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console", "file"],
            "level": "ERROR",
            "propagate": False,
        },
        "soundly": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "static")
