from unittest.mock import MagicMock, patch

import pytest
import requests

from workspaces.infrastructure.git.git_client import GitAPIClient
from workspaces.infrastructure.git.connection_service import ConnectionService
from workspaces.infrastructure.git.repository_fetcher import RepositoryFetcher


class ResponseStub:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else []

    def json(self):
        return self._payload


class TestGitAPIClient:
    def test_github_client_builds_url_and_headers(self):
        client = GitAPIClient("github", "tok")

        assert client.api_url == "https://api.github.com"
        assert client.headers["Authorization"] == "token tok"
        assert "github.v3" in client.headers["Accept"]

    def test_gitlab_client_builds_url_and_private_token_header(self):
        client = GitAPIClient("gitlab", "tok")

        assert client.api_url == "https://gitlab.com/api/v4"
        assert client.headers == {"PRIVATE-TOKEN": "tok"}

    def test_gitlab_self_requires_url_and_trims_trailing_slash(self):
        with pytest.raises(ValueError, match="URL required"):
            _ = GitAPIClient("gitlab_self", "tok").api_url

        client = GitAPIClient("gitlab_self", "tok", "https://git.example.com/")
        assert client.api_url == "https://git.example.com/api/v4"
        assert client.headers == {"Authorization": "Bearer tok"}

    @patch("workspaces.infrastructure.git.git_client.requests.get")
    def test_get_delegates_to_requests_with_headers_params_and_timeout(self, mock_get):
        client = GitAPIClient("github", "tok")
        mock_get.return_value = ResponseStub()

        response = client.get("/user/repos", params={"per_page": 1}, timeout=3)

        assert response.status_code == 200
        mock_get.assert_called_once_with(
            "https://api.github.com/user/repos",
            headers=client.headers,
            params={"per_page": 1},
            timeout=3,
        )


class TestRepositoryFetcher:
    @patch("workspaces.infrastructure.git.repository_fetcher.GitAPIClient")
    def test_fetch_all_github_success_normalizes_repositories(self, mock_client_cls):
        client = MagicMock()
        client.get.return_value = ResponseStub(
            200,
            [
                {
                    "id": 1,
                    "name": "repo",
                    "full_name": "owner/repo",
                    "html_url": "https://github.com/owner/repo",
                    "private": False,
                }
            ],
        )
        mock_client_cls.return_value = client

        result = RepositoryFetcher.fetch_all("github", "tok")

        assert result["success"] is True
        assert result["repositories"][0]["full_name"] == "owner/repo"
        client.get.assert_called_once_with(
            "/user/repos",
            params={
                "per_page": 100,
                "sort": "updated",
                "affiliation": "owner,collaborator,organization_member",
            },
        )

    @pytest.mark.parametrize(
        ("status_code", "message"),
        [
            (401, "Invalid or expired token"),
            (503, "API error: 503"),
        ],
    )
    @patch("workspaces.infrastructure.git.repository_fetcher.GitAPIClient")
    def test_fetch_all_handles_api_errors(self, mock_client_cls, status_code, message):
        client = MagicMock()
        client.get.return_value = ResponseStub(status_code, [])
        mock_client_cls.return_value = client

        result = RepositoryFetcher.fetch_all("gitlab", "tok")

        assert result == {"success": False, "message": message, "repositories": []}

    @pytest.mark.parametrize(
        ("exc", "message"),
        [
            (ValueError("URL required"), "URL required"),
            (requests.Timeout("slow"), "Timeout: server not responding"),
            (requests.ConnectionError("offline"), "Connection error: offline"),
        ],
    )
    @patch("workspaces.infrastructure.git.repository_fetcher.GitAPIClient")
    def test_fetch_all_handles_exceptions(self, mock_client_cls, exc, message):
        client = MagicMock()
        client.get.side_effect = exc
        mock_client_cls.return_value = client

        result = RepositoryFetcher.fetch_all("gitlab_self", "tok", "https://git.example.com")

        assert result == {"success": False, "message": message, "repositories": []}

    @patch("workspaces.infrastructure.git.repository_fetcher.GitAPIClient")
    def test_fetch_by_id_github_success(self, mock_client_cls):
        client = MagicMock()
        client.get.return_value = ResponseStub(200, {"id": 42, "name": "repo"})
        mock_client_cls.return_value = client

        result = RepositoryFetcher.fetch_by_id("github", "tok", "42")

        assert result["success"] is True
        assert result["repository"] == {"id": 42, "name": "repo"}
        client.get.assert_called_once_with("/repositories/42")

    @pytest.mark.parametrize(
        ("status_code", "message"),
        [
            (401, "Invalid or expired token"),
            (403, "Repository not found or inaccessible"),
            (404, "Repository not found or inaccessible"),
            (500, "API error: 500"),
        ],
    )
    @patch("workspaces.infrastructure.git.repository_fetcher.GitAPIClient")
    def test_fetch_by_id_handles_api_errors(self, mock_client_cls, status_code, message):
        client = MagicMock()
        client.get.return_value = ResponseStub(status_code, {})
        mock_client_cls.return_value = client

        result = RepositoryFetcher.fetch_by_id("gitlab", "tok", "group/repo")

        assert result == {"success": False, "message": message, "repository": None}
        client.get.assert_called_once_with("/projects/group%2Frepo")

    def test_list_params_are_platform_specific(self):
        assert RepositoryFetcher._list_params("github")["sort"] == "updated"
        assert RepositoryFetcher._list_params("gitlab")["membership"] is True


class TestConnectionService:
    @pytest.mark.parametrize(
        ("status_code", "expected"),
        [
            (200, {"success": True, "message": "Connection successful", "user_data": {"login": "alice"}}),
            (401, {"success": False, "message": "Invalid or expired token"}),
            (503, {"success": False, "message": "API error: 503"}),
        ],
    )
    def test_handle_response_maps_status_codes(self, status_code, expected):
        result = ConnectionService._handle_response(ResponseStub(status_code, {"login": "alice"}))

        assert result == expected

    @patch("workspaces.infrastructure.git.connection_service.GitAPIClient")
    def test_test_connection_success_delegates_to_git_client(self, mock_client_cls):
        client = MagicMock()
        client.get.return_value = ResponseStub(200, {"username": "alice"})
        mock_client_cls.return_value = client

        result = ConnectionService.test_connection("gitlab", "tok")

        assert result["success"] is True
        assert result["user_data"] == {"username": "alice"}
        client.get.assert_called_once_with("/user", timeout=10)

    @pytest.mark.parametrize(
        ("exc", "message"),
        [
            (ValueError("URL required"), "URL required"),
            (requests.Timeout("slow"), "Timeout: server not responding"),
            (requests.ConnectionError("offline"), "Connection error: offline"),
        ],
    )
    @patch("workspaces.infrastructure.git.connection_service.GitAPIClient")
    def test_test_connection_handles_exceptions(self, mock_client_cls, exc, message):
        client = MagicMock()
        client.get.side_effect = exc
        mock_client_cls.return_value = client

        assert ConnectionService.test_connection("gitlab_self", "tok") == {
            "success": False,
            "message": message,
        }
