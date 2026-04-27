"""Backward-compatibility shim.

Canonical location: ``collectors.infrastructure.providers.branch_fetcher``
"""
from collectors.infrastructure.providers.branch_fetcher import (  # noqa: F401
    BranchFetcher,
)

__all__ = ["BranchFetcher"]
