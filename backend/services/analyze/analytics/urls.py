from django.urls import path
from .devops_views import (
    KanbanListBoardsView,
    CICDListPipelinesView,
    KanbanCollectView,
    CICDCollectView,
    DevOpsDatasetsView,
    DevOpsDatasetDownloadView,
    DevOpsComputeMetricsView,
    DevOpsComputeMetricsCSVView,
    DevOpsJobStatusView,
)
from .views import (
    # Datasets
    DatasetListView,
    DatasetUploadView,
    DatasetDetailView,
    DatasetColumnsView,
    DatasetAvailableMetricsView,
    DatasetCompatibleAxesView,
    DatasetPreviewView,
    DatasetSummaryView,

    # Metrics
    MetricListView,
    MetricDetailView,
    MetricCategoriesView,
    MetricByCategoryView,

    # Analyses
    AnalysisListView,
    AnalysisBulkCreateView,
    AnalysisDetailView,
    AnalysisResultView,
    AnalysisRetryView,
    AnalysisHistoryView,

    # Generate (core endpoint)
    GenerateChartView,
)

urlpatterns = [

    # Datasets
    path('datasets/',                                       DatasetListView.as_view(),              name='dataset-list'),
    path('datasets/upload/',                                DatasetUploadView.as_view(),             name='dataset-upload'),
    path('datasets/<uuid:pk>/',                             DatasetDetailView.as_view(),             name='dataset-detail'),
    path('datasets/<uuid:pk>/columns/',                     DatasetColumnsView.as_view(),            name='dataset-columns'),
    path('datasets/<uuid:pk>/preview/',                     DatasetPreviewView.as_view(),            name='dataset-preview'),
    # Returns the list of metrics whose required_columns are present in the dataset
    path('datasets/<uuid:pk>/available_metrics/',           DatasetAvailableMetricsView.as_view(),   name='dataset-available-metrics'),
    # Returns compatible (x_axis, y_axis) pairs given the dataset columns
    path('datasets/<uuid:pk>/compatible_axes/',             DatasetCompatibleAxesView.as_view(),     name='dataset-compatible-axes'),
    path('datasets/<uuid:pk>/summary/',                     DatasetSummaryView.as_view(),            name='dataset-summary'),

    # ──────────────────────────────────────────
    # Metrics  (read-only catalogue)
    # ──────────────────────────────────────────
    path('metrics/',                                        MetricListView.as_view(),                name='metric-list'),
    # Static actions must come BEFORE <int:pk> to avoid Django resolving them as IDs
    path('metrics/categories/',                             MetricCategoriesView.as_view(),          name='metric-categories'),
    path('metrics/by_category/',                            MetricByCategoryView.as_view(),          name='metric-by-category'),
    path('metrics/<str:code>/',                             MetricDetailView.as_view(),              name='metric-detail'),

    # ──────────────────────────────────────────
    # Chart generation  (core feature)
    # POST  →  runs analysis, saves result, returns chart data + image
    # ──────────────────────────────────────────
    path('generate/',                                       GenerateChartView.as_view(),             name='generate-chart'),

    # Analyses  (history / re-run)
    # ──────────────────────────────────────────
    path('analyses/',                                       AnalysisListView.as_view(),              name='analysis-list'),
    path('analyses/bulk_create/',                           AnalysisBulkCreateView.as_view(),        name='analysis-bulk-create'),
    path('analyses/<uuid:pk>/',                             AnalysisDetailView.as_view(),            name='analysis-detail'),
    # Returns the saved chart_data + image of a past analysis
    path('analyses/<uuid:pk>/result/',                      AnalysisResultView.as_view(),            name='analysis-result'),
    # Re-runs the analysis (e.g. after a dataset update)
    path('analyses/<uuid:pk>/retry/',                       AnalysisRetryView.as_view(),             name='analysis-retry'),
    # History – grouped by dataset for the panel page
    path('analyses/history/',                               AnalysisHistoryView.as_view(),           name='analysis-history'),

    # ──────────────────────────────────────────
    # DevOps live collection (Kanban + CI/CD)
    # ──────────────────────────────────────────
    path('devops/kanban/boards/',      KanbanListBoardsView.as_view(),   name='devops-kanban-boards'),
    path('devops/kanban/collect/',     KanbanCollectView.as_view(),      name='devops-kanban-collect'),
    path('devops/cicd/pipelines/',     CICDListPipelinesView.as_view(),  name='devops-cicd-pipelines'),
    path('devops/cicd/collect/',       CICDCollectView.as_view(),        name='devops-cicd-collect'),
    path('devops/jobs/<uuid:pk>/status/', DevOpsJobStatusView.as_view(), name='devops-job-status'),
    path('devops/datasets/',                                DevOpsDatasetsView.as_view(),           name='devops-datasets'),
    path('devops/datasets/<uuid:pk>/download/',             DevOpsDatasetDownloadView.as_view(),    name='devops-dataset-download'),
    path('devops/datasets/<uuid:pk>/compute-metrics/',      DevOpsComputeMetricsView.as_view(),     name='devops-compute-metrics'),
    path('devops/datasets/<uuid:pk>/compute-metrics/csv/',  DevOpsComputeMetricsCSVView.as_view(),  name='devops-compute-metrics-csv'),
]
