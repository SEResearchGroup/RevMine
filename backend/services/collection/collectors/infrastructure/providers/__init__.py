"""Platform-specific data providers.

Houses the concrete collector implementations for GitHub and GitLab, the
single-item branch fetcher, and the abstract :class:`BaseCollector` interface.
"""
from collectors.infrastructure.providers.base import BaseCollector
from collectors.infrastructure.providers.github_fetcher import GitHubCollector
from collectors.infrastructure.providers.gitlab_fetcher import GitLabCollector
from collectors.infrastructure.providers.branch_fetcher import BranchFetcher

__all__ = ["BaseCollector", "GitHubCollector", "GitLabCollector", "BranchFetcher"]
