from django.urls import path
from collectors.api.views import (
    GetAvailableMetricsView,
    GetBranchesForRepositoryView,
    StartCollectionView,
    GetBranchesView,
    ConfigureMetricsView,
    UserDatasetsView,
    ValidateCollectionPlanView,
    ExecuteCollectionView,
    CollectionStatusView,
    CollectionPlanListView,
    CollectionHistoryView,
    CollectedDataView,
    DataCleaningConfigView,
    ApplyFiltersAndCreateCSVView,
    ResumeCollectionView,
    PauseCollectionView,
    CollectionCleanedDataListView,
    CreateCleanedDataView,
    CleanedDataDetailView,
    DownloadCleanedDataCSVView,
    DownloadCollectionJSONView,
    DeleteCollectionView,
    UploadExternalCollectionView,
    CleanedCollectionsForAnalysisView,
)

urlpatterns = [
    # Metrics and branches
    path("metrics/", GetAvailableMetricsView.as_view(), name="available-metrics"),
    path(
        "branches/", GetBranchesForRepositoryView.as_view(), name="repository-branches"
    ),
    # Collection workflow
    path("start/", StartCollectionView.as_view(), name="collection-start"),
    path(
        "plans/<int:plan_id>/configure/",
        ConfigureMetricsView.as_view(),
        name="collection-configure",
    ),
    path(
        "plans/<int:plan_id>/validate/",
        ValidateCollectionPlanView.as_view(),
        name="collection-validate",
    ),
    path(
        "plans/<int:plan_id>/execute/",
        ExecuteCollectionView.as_view(),
        name="collection-execute",
    ),
    path(
        "plans/<int:plan_id>/branches/",
        GetBranchesView.as_view(),
        name="collection-branches",
    ),
    path(
        "plans/<int:plan_id>/status/",
        CollectionStatusView.as_view(),
        name="collection-status",
    ),
    path(
        "plans/<int:plan_id>/data/", CollectedDataView.as_view(), name="collection-data"
    ),
    # Resume collection
    path(
        "plans/<int:plan_id>/resume/",
        ResumeCollectionView.as_view(),
        name="collection-resume",
    ),
    path(
        "plans/<int:plan_id>/pause/",
        PauseCollectionView.as_view(),
        name="collection-pause",
    ),
    # Data cleaning and structuring
    path(
        "plans/<int:plan_id>/cleaning-config/",
        DataCleaningConfigView.as_view(),
        name="data-cleaning-config",
    ),
    path(
        "plans/<int:plan_id>/apply-filters/",
        ApplyFiltersAndCreateCSVView.as_view(),
        name="apply-filters-csv",
    ),
    # Collection management
    path(
        "collections/<int:collection_id>/",
        CollectionStatusView.as_view(),
        name="collection-detail",
    ),
    path(
        "collections/<int:collection_id>/download/",
        DownloadCollectionJSONView.as_view(),
        name="download-collection-json",
    ),
    path(
        "collections/<int:collection_id>/delete/",
        DeleteCollectionView.as_view(),
        name="delete-collection",
    ),
    # CleanedData (cleaning operations)
    path(
        "collections/<int:collection_id>/cleaned-data/",
        CollectionCleanedDataListView.as_view(),
        name="collection-cleaned-data",
    ),
    path("cleaned-data/", CreateCleanedDataView.as_view(), name="create-cleaned-data"),
    path(
        "cleaned-data/<int:cleaned_data_id>/",
        CleanedDataDetailView.as_view(),
        name="cleaned-data-detail",
    ),
    path(
        "cleaned-data/<int:cleaned_data_id>/download/<str:file_type>/",
        DownloadCleanedDataCSVView.as_view(),
        name="download-cleaned-data-csv",
    ),
    # Lists and history
    path('plans/', CollectionPlanListView.as_view(), name='collection-plans'),
    path('history/<int:repository_id>/', CollectionHistoryView.as_view(), name='collection-history'),

    # External upload
    path('upload-external/', UploadExternalCollectionView.as_view(), name='upload-external-collection'),

    # get all user datasets
    path("datasets/", UserDatasetsView.as_view(), name="user-datasets"),

    # cleaned collections ready for analysis
    path("cleaned-for-analysis/", CleanedCollectionsForAnalysisView.as_view(), name="cleaned-for-analysis"),
]
