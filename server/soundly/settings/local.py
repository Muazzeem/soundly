"""
Local development settings override.
This file is imported by dev.py if it exists.
"""
import os
from .base import *

# Override database to use SQLite for local development (no Docker required)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.path.join(BASE_DIR, "db.sqlite3"),
    }
}

# Override database host for local PostgreSQL if needed
# Uncomment and modify if you want to use local PostgreSQL instead of SQLite
# DATABASES = {
#     "default": {
#         "ENGINE": "django.db.backends.postgresql",
#         "NAME": config("DB_NAME", default="soundly_db"),
#         "USER": config("DB_USER", default="postgres"),
#         "HOST": "localhost",  # Changed from "db" for local development
#         "PORT": 5432,
#     }
# }

