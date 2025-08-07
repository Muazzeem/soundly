import os

from .base import *

DEBUG = False
SECRET_KEY = config("SECRET_KEY")
ALLOWED_HOSTS = ["api.soundlybeats.com"]

CSRF_TRUSTED_ORIGINS = [
    "https://api.soundlybeats.com",
    "https://soundly-beats.vercel.app",
]

try:
    from .local import *
except ImportError:
    pass

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "..", "static")