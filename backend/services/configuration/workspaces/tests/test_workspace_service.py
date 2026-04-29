"""Unit and integration tests for WorkspaceService (application layer)."""
import pytest
from unittest.mock import patch, MagicMock

from workspaces.models import Workspace
from workspaces.services.workspace_service import WorkspaceService


GITHUB_OK_RESULT = {
    "success": True,
    "message": "Connection successful",
    "user_data": {"login": "testuser"},
}
GITHUB_FAIL_RESULT = {"success": False, "message": "Invalid or expired token"}


@pytest.mark.django_db
class TestCreateWorkspace:
    """Tests for WorkspaceService.create_workspace."""

    @patch(
        "workspaces.services.workspace_service.ConnectionService.test_connection",
        return_value=GITHUB_OK_RESULT,
    )
    def test_creates_workspace_on_success(self, mock_conn):
        data = {"name": "My WS", "platform": "github", "token": "ghp_test"}
        ws, conn = WorkspaceService.create_workspace(user_id=1, validated_data=data)

        assert ws.pk is not None
        assert ws.name == "My WS"
        assert ws.platform == "github"
        assert ws.user == 1
        assert ws.get_token() == "ghp_test"
        assert conn["success"] is True

    @patch(
        "workspaces.services.workspace_service.ConnectionService.test_connection",
        return_value=GITHUB_OK_RESULT,
    )
    def test_token_is_popped_from_data(self, mock_conn):
        data = {"name": "WS2", "platform": "github", "token": "ghp_abc"}
        WorkspaceService.create_workspace(user_id=1, validated_data=data)
        # token must have been consumed (popped)
        assert "token" not in data

    @patch(
        "workspaces.services.workspace_service.ConnectionService.test_connection",
        return_value=GITHUB_FAIL_RESULT,
    )
    def test_raises_on_failed_connection(self, mock_conn):
        data = {"name": "WS3", "platform": "github", "token": "bad_token"}
        with pytest.raises(ValueError, match="Invalid or expired token"):
            WorkspaceService.create_workspace(user_id=1, validated_data=data)
        assert not Workspace.objects.filter(name="WS3").exists()

    @patch(
        "workspaces.services.workspace_service.ConnectionService.test_connection",
        return_value=GITHUB_OK_RESULT,
    )
    def test_raises_on_duplicate_name(self, mock_conn, create_workspace):
        create_workspace(user_id=5, name="Duplicate")
        data = {"name": "Duplicate", "platform": "github", "token": "ghp_x"}
        with pytest.raises(ValueError, match="already exists"):
            WorkspaceService.create_workspace(user_id=5, validated_data=data)

    def test_raises_on_unsupported_platform(self):
        data = {"name": "Bad WS", "platform": "bitbucket", "token": "tok"}
        with pytest.raises(ValueError, match="Unsupported platform"):
            WorkspaceService.create_workspace(user_id=1, validated_data=data)

    def test_raises_on_gitlab_self_without_url(self):
        data = {"name": "Self WS", "platform": "gitlab_self", "token": "tok"}
        with pytest.raises(ValueError, match="URL is required"):
            WorkspaceService.create_workspace(user_id=1, validated_data=data)


@pytest.mark.django_db
class TestUpdateWorkspace:
    """Tests for WorkspaceService.update_workspace."""

    @patch(
        "workspaces.services.workspace_service.ConnectionService.test_connection",
        return_value=GITHUB_OK_RESULT,
    )
    def test_updates_name_without_token(self, mock_conn, create_workspace):
        ws = create_workspace(user_id=1, name="Old Name")
        updated = WorkspaceService.update_workspace(
            ws, {"name": "New Name"}
        )
        assert updated.name == "New Name"
        mock_conn.assert_not_called()

    @patch(
        "workspaces.services.workspace_service.ConnectionService.test_connection",
        return_value=GITHUB_OK_RESULT,
    )
    def test_updates_token_when_provided(self, mock_conn, create_workspace):
        ws = create_workspace(user_id=1)
        updated = WorkspaceService.update_workspace(ws, {}, token="new_token")
        assert updated.get_token() == "new_token"
        mock_conn.assert_called_once()

    @patch(
        "workspaces.services.workspace_service.ConnectionService.test_connection",
        return_value=GITHUB_FAIL_RESULT,
    )
    def test_raises_on_bad_new_token(self, mock_conn, create_workspace):
        ws = create_workspace(user_id=1)
        with pytest.raises(ValueError, match="Invalid or expired token"):
            WorkspaceService.update_workspace(ws, {}, token="bad_token")
