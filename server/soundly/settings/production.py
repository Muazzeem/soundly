import os

from .base import *

DEBUG = False
SECRET_KEY = config("SECRET_KEY")
ALLOWED_HOSTS = ["*"]

CSRF_TRUSTED_ORIGINS = [
    "https://soundly-beats.vercel.app",
]

try:
    from .local import *
except ImportError:
    pass
