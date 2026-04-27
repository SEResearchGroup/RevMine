"""URL configuration for the collectors app.

This module delegates to :mod:`collectors.api.urls` so that the URL patterns
remain in the canonical API layer while this file serves as the Django-app
entry point referenced in ``collect/urls.py``.
"""
from collectors.api.urls import urlpatterns  # noqa: F401
