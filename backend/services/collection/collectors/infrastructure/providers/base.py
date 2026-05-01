"""Abstract base provider interface.

All platform-specific data collectors must implement this interface,
ensuring a consistent API regardless of the upstream platform (GitHub, GitLab, …).
"""
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional


class BaseCollector(ABC):
    """Abstract base class for platform-specific data collectors.

    Subclasses must implement :meth:`collect_all_data` which drives the full
    collection pipeline: pagination, resume support, and progress reporting.
    """

    def __init__(
        self,
        token: str,
        repo_full_name: str,
        branch_name: Optional[str] = None,
        selected_metrics: Optional[List[str]] = None,
    ) -> None:
        self.token = token
        self.repo_full_name = repo_full_name
        self.branch_name = branch_name
        self.selected_metrics = selected_metrics or []
        self.required_endpoints: Optional[List[str]] = None
        self.is_total_approximate: bool = False

    @abstractmethod
    def collect_all_data(
        self,
        filters: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[Callable] = None,
        resume_from: Optional[str] = None,
        existing_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Collect all pull-request / merge-request data.

        Args:
            filters: Date/status filters to restrict the collection window.
            progress_callback: ``callback(current, total, message, item_data, all_data)``
                called after each item is collected.
            resume_from: Item number / IID to start from (resume mode).
            existing_data: Already-collected data dict to extend (resume mode).

        Returns:
            A dict whose top-level key is ``pull_requests`` (GitHub) or
            ``merge_requests`` (GitLab), plus optional metadata keys such as
            ``project_created_at``.
        """
