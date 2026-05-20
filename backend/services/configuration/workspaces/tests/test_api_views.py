"""Integration tests for workspaces and repositories API endpoints."""
import pytest
from unittest.mock import patch
from rest_framework import status

from workspaces.models import Workspace, Repository
from workspaces.services.repository_service import RepositoryService


CONN_OK = {
    "success": True,
    "message": "Connection successful",
    "user_data": {"login": "testuser"},
}
CONN_FAIL = {"success": False, "message": "Invalid or expired token"}


# ---------------------------------------------------------------------------
# Workspace list / create
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestWorkspaceListCreate:

    def test_list_unauthenticated_returns_401(self, unauthenticated_client):
        resp = unauthenticated_client.get("/api/workspaces/")
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_authenticated_returns_200(self, api_client, workspace):
        resp = api_client.get("/api/workspaces/")
        assert resp.status_code == status.HTTP_200_OK

    @patch(
        "workspaces.services.workspace_service.ConnectionService.test_connection",
        return_value=CONN_OK,
    )
    def test_create_workspace_success(self, _mock, api_client, workspace_data):
        resp = api_client.post("/api/workspaces/", workspace_data)
        assert resp.status_code == status.HTTP_201_CREATED
        assert "workspace" in resp.data
        assert resp.data["workspace"]["name"] == workspace_data["name"]

    def test_create_workspace_invalid_platform(self, api_client, workspace_data):
        workspace_data["platform"] = "bitbucket"
        resp = api_client.post("/api/workspaces/", workspace_data)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_workspace_gitlab_self_requires_url(
        self, api_client, gitlab_self_workspace_data
    ):
        del gitlab_self_workspace_data["url"]
        resp = api_client.post("/api/workspaces/", gitlab_self_workspace_data)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    @patch(
        "workspaces.services.workspace_service.ConnectionService.test_connection",
        return_value=CONN_OK,
    )
    def test_create_duplicate_name_returns_400(
        self, _mock, api_client, workspace, workspace_data
    ):
        workspace_data["name"] = workspace.name
        resp = api_client.post("/api/workspaces/", workspace_data)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "already exists" in str(resp.data).lower()


# ---------------------------------------------------------------------------
# Workspace detail / update / delete
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestWorkspaceDetail:

    def test_get_workspace_returns_200(self, api_client, workspace):
        resp = api_client.get(f"/api/workspaces/{workspace.id}/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["name"] == workspace.name

    def test_get_nonexistent_workspace_returns_404(self, api_client):
        resp = api_client.get("/api/workspaces/99999/")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    @patch(
        "workspaces.services.workspace_service.ConnectionService.test_connection",
        return_value=CONN_OK,
    )
    def test_patch_name_returns_200(self, _mock, api_client, workspace):
        resp = api_client.patch(
            f"/api/workspaces/{workspace.id}/", {"name": "Updated Name"}
        )
        assert resp.status_code == status.HTTP_200_OK
        workspace.refresh_from_db()
        assert workspace.name == "Updated Name"

    def test_delete_workspace_returns_204(self, api_client, workspace):
        resp = api_client.delete(f"/api/workspaces/{workspace.id}/")
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        assert not Workspace.objects.filter(id=workspace.id).exists()

    def test_delete_cascades_repositories(self, api_client, workspace, create_repository):
        repo = create_repository(workspace=workspace)
        api_client.delete(f"/api/workspaces/{workspace.id}/")
        assert not Repository.objects.filter(id=repo.id).exists()


# ---------------------------------------------------------------------------
# Repository list / detail / delete
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestRepositoryEndpoints:

    def test_list_repositories_returns_200(self, api_client, workspace, create_repository):
        create_repository(workspace=workspace)
        resp = api_client.get(f"/api/workspaces/{workspace.id}/repositories/")
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) >= 1

    def test_get_repository_detail(self, api_client, workspace, create_repository):
        repo = create_repository(workspace=workspace)
        resp = api_client.get(
            f"/api/workspaces/{workspace.id}/repositories/{repo.id}/"
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["name"] == repo.name

    def test_delete_repository_returns_204(self, api_client, workspace, create_repository):
        repo = create_repository(workspace=workspace)
        resp = api_client.delete(
            f"/api/workspaces/{workspace.id}/repositories/{repo.id}/"
        )
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        assert not Repository.objects.filter(id=repo.id).exists()


# ---------------------------------------------------------------------------
# Repository import
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestRepositoryImport:

    @patch.object(
        RepositoryService,
        "fetch_repository_by_id",
        return_value={
            "success": True,
            "message": "Repository found",
            "repository": {
                "id": 987654321,
                "name": "public-repo",
                "full_name": "octocat/public-repo",
                "description": "A public repository",
                "url": "https://api.github.com/repos/octocat/public-repo",
                "html_url": "https://github.com/octocat/public-repo",
                "owner": {"login": "octocat", "type": "User"},
                "default_branch": "main",
                "private": False,
                "fork": False,
                "archived": False,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-02-01T00:00:00Z",
            },
        },
    )
    @patch.object(
        RepositoryService,
        "fetch_repositories",
        return_value={"success": True, "message": "0 repositories found", "repositories": []},
    )
    def test_import_by_external_id_returns_201(
        self, _mock_all, _mock_by_id, api_client, workspace
    ):
        resp = api_client.post(
            f"/api/workspaces/{workspace.id}/repositories/import/",
            {"repository_ids": ["987654321"]},
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["imported_count"] == 1
        assert Repository.objects.filter(
            workspace=workspace, external_id="987654321"
        ).exists()

    def test_import_empty_ids_returns_400(self, api_client, workspace):
        resp = api_client.post(
            f"/api/workspaces/{workspace.id}/repositories/import/",
            {"repository_ids": []},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    @patch.object(
        RepositoryService,
        "import_repositories",
        return_value=(
            [],
            [{"repository": "My-Portfolio", "error": "Repository owner could not be determined"}],
        ),
    )
    def test_import_with_only_errors_returns_400_and_success_false(
        self, _mock_import, api_client, workspace
    ):
        resp = api_client.post(
            f"/api/workspaces/{workspace.id}/repositories/import/",
            {"repository_ids": ["709287984"]},
            format="json",
        )

        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.data["success"] is False
        assert resp.data["imported_count"] == 0
        assert resp.data["errors"][0]["repository"] == "My-Portfolio"


# ---------------------------------------------------------------------------
# Connection test endpoint
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestConnectionEndpoint:

    @patch(
        "workspaces.api.views.ConnectionService.test_connection",
        return_value=CONN_OK,
    )
    def test_test_connection_success(self, _mock, api_client):
        resp = api_client.post(
            "/api/workspaces/test/",
            {"platform": "github", "token": "ghp_valid"},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["success"] is True

    @patch(
        "workspaces.api.views.ConnectionService.test_connection",
        return_value=CONN_FAIL,
    )
    def test_test_connection_failure_returns_400(self, _mock, api_client):
        resp = api_client.post(
            "/api/workspaces/test/",
            {"platform": "github", "token": "bad_token"},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.data["success"] is False
