from django.urls import path

from workspaces.api.views import (
    WorkspaceListCreateView,
    WorkspaceDetailView,
    WorkspaceTokenView,
    WorkspaceTestConnectionView,
    WorkspaceRepositoriesView,
    RepositoryImportView,
    RepositoryListView,
    RepositoryDetailView,
    AllRepositoriesView,
)

urlpatterns = [
    # ===== All Repositories (across workspaces) =====
    path(
        "workspaces/repositories/all/",
        AllRepositoriesView.as_view(),
        name="all-repositories",
    ),
    # ===== Workspaces =====
    path(
        "workspaces/",
        WorkspaceListCreateView.as_view(),
        name="workspace-list-create",
    ),
    path(
        "workspaces/<int:workspace_id>/",
        WorkspaceDetailView.as_view(),
        name="workspace-detail",
    ),
    path(
        "workspaces/<int:workspace_id>/token/",
        WorkspaceTokenView.as_view(),
        name="workspace-token",
    ),
    path(
        "workspaces/test/",
        WorkspaceTestConnectionView.as_view(),
        name="workspace-test-global",
    ),
    path(
        "workspaces/<int:workspace_id>/test/",
        WorkspaceTestConnectionView.as_view(),
        name="workspace-test",
    ),
    path(
        "workspaces/<int:workspace_id>/remote-repositories/",
        WorkspaceRepositoriesView.as_view(),
        name="workspace-remote-repositories",
    ),
    path(
        "workspaces/<int:workspace_id>/repositories/import/",
        RepositoryImportView.as_view(),
        name="repository-import",
    ),
    path(
        "workspaces/<int:workspace_id>/repositories/",
        RepositoryListView.as_view(),
        name="repository-list",
    ),
    path(
        "workspaces/<int:workspace_id>/repositories/<int:repository_id>/",
        RepositoryDetailView.as_view(),
        name="repository-detail",
    ),
]
