from django.urls import path
from .views import (
    AnalysisExportView,
    AnalysisListView,
    AnalysisDetailView,
    DatasetListView,
    DatasetDetailView,
    AnalysisResultDetailView,
    AnalysisCreateView,
)

urlpatterns = [
    path("", AnalysisListView.as_view(), name="analysis-list"),  # GET
    path("create/", AnalysisCreateView.as_view(), name="analysis-create"),
    path(
        "<uuid:analysis_id>/", AnalysisDetailView.as_view(), name="analysis-detail"
    ),  # GET, PUT, DELETE
    path("datasets/", DatasetListView.as_view(), name="dataset-list"),  # GET
    path(
        "datasets/<uuid:dataset_id>/",
        DatasetDetailView.as_view(),
        name="dataset-detail",
    ),  # GET
    path(
        "results/<uuid:result_id>/",
        AnalysisResultDetailView.as_view(),
        name="result-detail",
    ),  # GET
    path(
        "analyses/<uuid:analysis_id>/export/",
        AnalysisExportView.as_view(),
        name="analysis-export",
    ),  # NEW
]
