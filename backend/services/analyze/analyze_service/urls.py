from django.urls import path, include
from django.contrib import admin

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/analysis/", include("analytics.urls")),
    path("api/analysis/", include("analytics.urls")),
]
