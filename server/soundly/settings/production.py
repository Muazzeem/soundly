import os

from .base import *

DEBUG = config("DEBUG", default=False, cast=bool)
SECRET_KEY = config("SECRET_KEY")
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="api.soundlybeats.com").split(",")

CSRF_TRUSTED_ORIGINS = config(
    "CSRF_TRUSTED_ORIGINS",
    default="https://api.soundlybeats.com,https://soundly-beats.vercel.app"
).split(",")

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

try:
    from .local import *
except ImportError:
    pass
