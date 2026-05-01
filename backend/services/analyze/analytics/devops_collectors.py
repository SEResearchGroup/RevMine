# Backward-compatibility shim — do not add logic here.
from analytics.infrastructure.collectors.devops_collectors import (  # noqa: F401
    GitHubActionsCollector,
    GitHubProjectsCollector,
    GitLabBoardsCollector,
    GitLabCICollector,
)
__all__ = [
    "GitHubActionsCollector",
    "GitHubProjectsCollector",
    "GitLabBoardsCollector",
    "GitLabCICollector",
]
