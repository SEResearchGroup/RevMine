from django.urls import path

from quality.api.views import (
    DatasetListView,
    DatasetDetailView,
    DatasetRebuildView,
    CommentListView,
    CommentDetailView,
    FacetsView,
    TimeseriesView,
    StartAnalysisView,
)

urlpatterns = [
    path("datasets/", DatasetListView.as_view(), name="qualitative-dataset-list"),
    path("datasets/<uuid:dataset_id>/", DatasetDetailView.as_view(), name="qualitative-dataset-detail"),
    path("datasets/<uuid:dataset_id>/rebuild/", DatasetRebuildView.as_view(), name="qualitative-dataset-rebuild"),
    path("datasets/<uuid:dataset_id>/comments/", CommentListView.as_view(), name="qualitative-comment-list"),
    path("datasets/<uuid:dataset_id>/comments/<int:comment_id>/", CommentDetailView.as_view(), name="qualitative-comment-detail"),
    path("datasets/<uuid:dataset_id>/facets/", FacetsView.as_view(), name="qualitative-facets"),
    path("datasets/<uuid:dataset_id>/timeseries/", TimeseriesView.as_view(), name="qualitative-timeseries"),
    path("datasets/<uuid:dataset_id>/analyses/", StartAnalysisView.as_view(), name="qualitative-start-analysis"),
]
