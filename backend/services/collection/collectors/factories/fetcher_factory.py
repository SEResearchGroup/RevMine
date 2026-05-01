"""Fetcher Factory — instantiate the correct platform provider.

This factory is the single authoritative place that maps a platform name to
its concrete :class:`~collectors.infrastructure.providers.base.BaseCollector`
implementation.  Views and service classes should obtain collectors through
this factory rather than importing ``GitHubCollector`` / ``GitLabCollector``
directly, which keeps the callers decoupled from the concrete types.

Usage::

    from collectors.factories.fetcher_factory import FetcherFactory

    collector = FetcherFactory.create(
        platform="github",
        token="ghp_...",
        repo_full_name="owner/repo",
        branch_name="main",
        selected_metrics=["pr_title", "commit_sha"],
        project_id=None,
    )
    data = collector.collect_all_data(filters={"start_date": date(2024, 1, 1)})
"""

from typing import List, Optional

from collectors.infrastructure.providers.base import BaseCollector
from collectors.infrastructure.providers.github_fetcher import GitHubCollector
from collectors.infrastructure.providers.gitlab_fetcher import GitLabCollector


class FetcherFactory:
    """Factory that creates platform-specific data collectors."""

    _REGISTRY = {
        "github": GitHubCollector,
        "gitlab": GitLabCollector,
        "gitlab_self": GitLabCollector,  # self-hosted GitLab uses the same collector
    }

    @classmethod
    def create(
        cls,
        platform: str,
        token: str,
        repo_full_name: str,
        branch_name: Optional[str] = None,
        selected_metrics: Optional[List[str]] = None,
        project_id: Optional[str] = None,
    ) -> BaseCollector:
        """Instantiate the correct collector for *platform*.

        Args:
            platform: ``"github"``, ``"gitlab"``, or ``"gitlab_self"``.
            token: Personal access / OAuth token for the Git API.
            repo_full_name: ``"owner/repo"`` path (GitHub) or namespace/project (GitLab).
            branch_name: Optional target branch (base branch for GitHub PRs).
            selected_metrics: Metric IDs to collect (used to skip unneeded endpoints).
            project_id: GitLab numeric project ID when already known (avoids an
                extra API round-trip to resolve it from the full name).

        Returns:
            A :class:`BaseCollector` instance ready to call :meth:`collect_all_data`.

        Raises:
            ValueError: If *platform* is not registered.
        """
        platform_key = platform.lower()
        collector_cls = cls._REGISTRY.get(platform_key)

        if collector_cls is None:
            supported = ", ".join(cls._REGISTRY)
            raise ValueError(
                f"Unsupported platform '{platform}'. Supported: {supported}"
            )

        if platform_key == "github":
            return collector_cls(
                token=token,
                repo_full_name=repo_full_name,
                branch_name=branch_name,
                selected_metrics=selected_metrics,
            )

        # GitLab (hosted or self-hosted)
        return collector_cls(
            token=token,
            repo_full_name=repo_full_name,
            branch_name=branch_name,
            project_id=project_id,
            selected_metrics=selected_metrics,
        )
