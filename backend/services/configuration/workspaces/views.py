# Compatibility shim: API views live in workspaces.api.views.
from workspaces.api.views import (
    AllRepositoriesView,
    RepositoryDetailView,
    RepositoryImportView,
    RepositoryListView,
    WorkspaceDetailView,
    WorkspaceListCreateView,
    WorkspaceRepositoriesView,
    WorkspaceTestConnectionView,
    WorkspaceTokenView,
)

__all__ = [
    "WorkspaceListCreateView",
    "WorkspaceDetailView",
    "WorkspaceTokenView",
    "WorkspaceTestConnectionView",
    "WorkspaceRepositoriesView",
    "RepositoryImportView",
    "RepositoryListView",
    "RepositoryDetailView",
    "AllRepositoriesView",
]
