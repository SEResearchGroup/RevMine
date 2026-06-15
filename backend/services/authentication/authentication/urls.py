from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/auth/", include("users.urls")),
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
    path("api/auth/", include("users.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]
