"""Backward-compatibility shim.

Canonical location: ``collectors.infrastructure.exporters.csv_generator``.
"""
from collectors.infrastructure.exporters.csv_generator import (  # noqa: F401
    CSVGenerator,
    DataExtractor,
    GitHubAdapter,
    GitHubDataExtractor,
    GitLabAdapter,
    GitLabDataExtractor,
    MetricsCalculator,
    PlatformAdapter,
    StatisticsCSVGenerator,
    _dig,
    get_data_extractor,
    get_platform_adapter,
)

__all__ = [
    "_dig",
    "DataExtractor",
    "GitHubDataExtractor",
    "GitLabDataExtractor",
    "get_data_extractor",
    "MetricsCalculator",
    "CSVGenerator",
    "PlatformAdapter",
    "GitHubAdapter",
    "GitLabAdapter",
    "get_platform_adapter",
    "StatisticsCSVGenerator",
]
