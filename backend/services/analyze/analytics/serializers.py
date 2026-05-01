# Backward-compatibility shim — do not add logic here.
from analytics.api.serializers import (  # noqa: F401
    DatasetSerializer,
    DatasetUploadSerializer,
    MetricDefinitionSerializer,
    AnalysisSerializer,
    AnalysisListSerializer,
    AnalysisResultSerializer,
    AnalysisBatchSerializer,
)
# Alias for old callers that used BatchAnalysisSerializer
BatchAnalysisSerializer = AnalysisBatchSerializer  # noqa: F401
__all__ = [
    "DatasetSerializer",
    "DatasetUploadSerializer",
    "MetricDefinitionSerializer",
    "AnalysisSerializer",
    "AnalysisListSerializer",
    "AnalysisResultSerializer",
    "BatchAnalysisSerializer",
    "AnalysisBatchSerializer",
]
