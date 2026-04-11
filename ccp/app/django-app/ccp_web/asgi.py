"""ASGI entry point for the ccp web application."""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ccp_web.settings")

application = get_asgi_application()
