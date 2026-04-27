"""Backward-compatibility shim.

Canonical location: ``collectors.infrastructure.providers.github_fetcher``
"""
from collectors.infrastructure.providers.github_fetcher import (  # noqa: F401
    GitHubCollector,
    _create_session,
)

__all__ = ["GitHubCollector", "_create_session"]
