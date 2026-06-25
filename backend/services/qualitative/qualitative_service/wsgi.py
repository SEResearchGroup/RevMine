"""WSGI config for the qualitative service."""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "qualitative_service.settings")

application = get_wsgi_application()
