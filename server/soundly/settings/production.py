import os

from .base import *

DEBUG = True
SECRET_KEY = config("SECRET_KEY")
ALLOWED_HOSTS = ["api.soundlybeats.com"]

CSRF_TRUSTED_ORIGINS = [
    "https://api.soundlybeats.com",
    "https://soundly-beats.vercel.app",
]

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

try:
    from .local import *
except ImportError:
    pass
