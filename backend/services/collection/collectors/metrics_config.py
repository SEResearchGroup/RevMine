"""Backward-compatibility shim.

Canonical location: ``collectors.domain.entities.metrics_config``
"""
from collectors.domain.entities.metrics_config import (  # noqa: F401
    GITHUB_METRICS,
    GITLAB_METRICS,
    get_metrics_for_platform,
    get_all_metric_values,
    get_category_metric_values,
    get_required_endpoints,
)

__all__ = [
    "GITHUB_METRICS",
    "GITLAB_METRICS",
    "get_metrics_for_platform",
    "get_all_metric_values",
    "get_category_metric_values",
    "get_required_endpoints",
]
