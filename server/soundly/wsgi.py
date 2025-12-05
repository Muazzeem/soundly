import os

from django.core.wsgi import get_wsgi_application

# DJANGO_SETTINGS_MODULE should be set via environment variable
# Do not set a default here to avoid accidentally using wrong settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "soundly.settings.production")

application = get_wsgi_application()
