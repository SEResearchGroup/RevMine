"""workspaces.services package — backward-compatibility exports.

All original symbols from the flat ``services.py`` are re-exported here so
that existing code using ``from workspaces.services import X`` continues to
work without modification.
"""
from workspaces.infrastructure.git.git_client import GitAPIClient
from workspaces.infrastructure.git.connection_service import ConnectionService
from workspaces.services.repository_service import RepositoryService
from workspaces.services.workspace_service import WorkspaceService

__all__ = [
    "GitAPIClient",
    "ConnectionService",
    "RepositoryService",
    "WorkspaceService",
]
