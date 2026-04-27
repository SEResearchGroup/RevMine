"""Domain entities — metric definitions and configuration constants."""
from collectors.domain.entities.metrics_config import (
    GITHUB_METRICS,
    GITLAB_METRICS,
    get_metrics_for_platform,
    get_required_endpoints,
)

__all__ = [
    "GITHUB_METRICS",
    "GITLAB_METRICS",
    "get_metrics_for_platform",
    "get_required_endpoints",
]
