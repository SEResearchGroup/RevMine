from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/qualitative/", include("quality.api.urls")),
    path("api/qualitative/", include("quality.api.urls")),

    # API Documentation
    path("api/v1/schema/", SpectacularAPIView.as_view(), name="schema-v1"),
    path(
        "api/v1/docs/",
        SpectacularSwaggerView.as_view(url_name="schema-v1"),
        name="swagger-ui-v1",
    ),
    path(
        "api/v1/redoc/",
        SpectacularRedocView.as_view(url_name="schema-v1"),
        name="redoc-v1",
    ),
]
