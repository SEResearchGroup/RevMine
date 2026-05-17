"""Backward-compatibility shim.

Canonical location: ``collectors.infrastructure.providers.gitlab_fetcher``.
"""
from collectors.infrastructure.providers.gitlab_fetcher import (  # noqa: F401
    GitLabCollector,
    _create_session,
)

__all__ = ["GitLabCollector", "_create_session"]
