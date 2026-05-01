# Backward-compatibility shim — do not add logic here.
from analytics.api.devops_views import (  # noqa: F401
    KanbanListBoardsView,
    CICDListPipelinesView,
    KanbanCollectView,
    CICDCollectView,
    DevOpsJobStatusView,
    DevOpsDatasetDownloadView,
    DevOpsComputeMetricsView,
    DevOpsComputeMetricsCSVView,
    DevOpsDatasetsView,
)
__all__ = [
    "KanbanListBoardsView", "CICDListPipelinesView",
    "KanbanCollectView", "CICDCollectView",
    "DevOpsJobStatusView", "DevOpsDatasetDownloadView",
    "DevOpsComputeMetricsView", "DevOpsComputeMetricsCSVView", "DevOpsDatasetsView",
]
