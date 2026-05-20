"""Unit tests for RepositoryService (application layer) and RepositoryFetcher."""
import pytest
from unittest.mock import patch, MagicMock

from workspaces.models import Repository
from workspaces.services.repository_service import RepositoryService


MOCK_GITHUB_REPO = {
    "id": 123456,
    "name": "my-repo",
    "full_name": "owner/my-repo",
    "description": "A test repository",
    "url": "https://api.github.com/repos/owner/my-repo",
    "html_url": "https://github.com/owner/my-repo",
    "owner": {"login": "owner", "type": "User"},
    "default_branch": "main",
    "private": False,
    "fork": False,
    "archived": False,
    "stargazers_count": 5,
    "forks_count": 2,
    "open_issues_count": 1,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-06-01T00:00:00Z",
}

FETCH_ALL_SUCCESS = {
    "success": True,
    "message": "1 repositories found",
    "repositories": [MOCK_GITHUB_REPO],
}

FETCH_ALL_EMPTY = {
    "success": True,
    "message": "0 repositories found",
    "repositories": [],
}

FETCH_BY_ID_SUCCESS = {
    "success": True,
    "message": "Repository found",
    "repository": MOCK_GITHUB_REPO,
}

FETCH_BY_ID_FAIL = {
    "success": False,
    "message": "Repository not found or inaccessible",
    "repository": None,
}

LIGHTWEIGHT_GITHUB_REPO = {
    "id": 709287984,
    "name": "My-Portfolio",
    "full_name": "ousscher/My-Portfolio",
    "description": "Portfolio website",
    "url": "https://github.com/ousscher/My-Portfolio",
    "clone_url": "https://github.com/ousscher/My-Portfolio.git",
    "default_branch": "main",
    "private": False,
    "language": "JavaScript",
    "updated_at": "2026-03-30T16:42:57Z",
}


@pytest.mark.django_db
class TestImportRepositories:
    """Tests for RepositoryService.import_repositories."""

    @patch.object(RepositoryService, "fetch_repositories", return_value=FETCH_ALL_SUCCESS)
    def test_imports_from_listing(self, mock_fetch, workspace):
        imported, errors = RepositoryService.import_repositories(workspace, ["123456"])
        assert len(imported) == 1
        assert errors == []
        assert imported[0].external_id == "123456"
        assert Repository.objects.filter(workspace=workspace, external_id="123456").exists()

    @patch.object(
        RepositoryService,
        "fetch_repositories",
        return_value={
            "success": True,
            "message": "1 repositories found",
            "repositories": [LIGHTWEIGHT_GITHUB_REPO],
        },
    )
    def test_imports_from_lightweight_listing_derives_owner_from_full_name(
        self, mock_fetch, workspace
    ):
        imported, errors = RepositoryService.import_repositories(workspace, ["709287984"])

        assert errors == []
        assert len(imported) == 1
        assert imported[0].owner == "ousscher"

    @patch.object(RepositoryService, "fetch_repository_by_id", return_value=FETCH_BY_ID_SUCCESS)
    @patch.object(RepositoryService, "fetch_repositories", return_value=FETCH_ALL_EMPTY)
    def test_falls_back_to_direct_lookup(self, mock_all, mock_by_id, workspace):
        imported, errors = RepositoryService.import_repositories(workspace, ["123456"])
        mock_by_id.assert_called_once()
        assert len(imported) == 1
        assert errors == []

    @patch.object(RepositoryService, "fetch_repository_by_id", return_value=FETCH_BY_ID_FAIL)
    @patch.object(RepositoryService, "fetch_repositories", return_value=FETCH_ALL_EMPTY)
    def test_records_error_for_inaccessible_repo(self, mock_all, mock_by_id, workspace):
        with pytest.raises(ValueError, match="not found or inaccessible"):
            RepositoryService.import_repositories(workspace, ["999999"])

    @patch.object(RepositoryService, "fetch_repositories", return_value=FETCH_ALL_SUCCESS)
    def test_deduplicates_ids(self, mock_fetch, workspace):
        imported, errors = RepositoryService.import_repositories(
            workspace, ["123456", "123456", " 123456 "]
        )
        assert len(imported) == 1  # deduped to a single repo

    @patch.object(RepositoryService, "fetch_repositories", return_value=FETCH_ALL_SUCCESS)
    def test_upserts_existing_repository(self, mock_fetch, workspace, create_repository):
        create_repository(workspace=workspace, external_id="123456", name="old-name")
        imported, _ = RepositoryService.import_repositories(workspace, ["123456"])
        assert imported[0].name == "my-repo"  # updated to API name

    @patch.object(RepositoryService, "fetch_repositories")
    def test_raises_when_listing_fails(self, mock_fetch, workspace):
        mock_fetch.return_value = {
            "success": False,
            "message": "Invalid token",
            "repositories": [],
        }
        with pytest.raises(Exception, match="Invalid token"):
            RepositoryService.import_repositories(workspace, ["1"])


@pytest.mark.django_db
class TestFetchRepositoriesProxy:
    """Verify that RepositoryService proxies correctly to RepositoryFetcher."""

    @patch("workspaces.services.repository_service.RepositoryFetcher.fetch_all")
    def test_fetch_repositories_delegates(self, mock_fetcher, workspace):
        mock_fetcher.return_value = FETCH_ALL_SUCCESS
        result = RepositoryService.fetch_repositories("github", "tok", None)
        mock_fetcher.assert_called_once_with("github", "tok", None)
        assert result["success"] is True

    @patch("workspaces.services.repository_service.RepositoryFetcher.fetch_by_id")
    def test_fetch_repository_by_id_delegates(self, mock_fetcher, workspace):
        mock_fetcher.return_value = FETCH_BY_ID_SUCCESS
        result = RepositoryService.fetch_repository_by_id("github", "tok", "123")
        mock_fetcher.assert_called_once_with("github", "tok", "123", None)
        assert result["success"] is True
