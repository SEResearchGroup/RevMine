"""Unit tests for the infrastructure layer.

Tests cover:
- MinIOClient behaviour (storage)
- FetcherFactory instantiation
- GitHubCollector / GitLabCollector session creation
- BranchFetcher routing
"""
import pytest
from unittest.mock import MagicMock, patch, PropertyMock

from collectors.factories.fetcher_factory import FetcherFactory
from collectors.infrastructure.providers.github_fetcher import GitHubCollector
from collectors.infrastructure.providers.gitlab_fetcher import GitLabCollector
from collectors.infrastructure.providers.branch_fetcher import BranchFetcher
from collectors.infrastructure.providers.base import BaseCollector


# =============================================================================
# FetcherFactory
# =============================================================================

class TestFetcherFactory:
    def test_creates_github_collector(self):
        collector = FetcherFactory.create(
            platform="github",
            token="tok",
            repo_full_name="owner/repo",
        )
        assert isinstance(collector, GitHubCollector)

    def test_creates_gitlab_collector(self):
        collector = FetcherFactory.create(
            platform="gitlab",
            token="tok",
            repo_full_name="owner/repo",
        )
        assert isinstance(collector, GitLabCollector)

    def test_gitlab_self_maps_to_gitlab_collector(self):
        collector = FetcherFactory.create(
            platform="gitlab_self",
            token="tok",
            repo_full_name="owner/repo",
        )
        assert isinstance(collector, GitLabCollector)

    def test_unknown_platform_raises_value_error(self):
        with pytest.raises(ValueError, match="Unsupported platform"):
            FetcherFactory.create(platform="bitbucket", token="t", repo_full_name="o/r")

    def test_github_collector_attributes(self):
        collector = FetcherFactory.create(
            platform="github",
            token="mytoken",
            repo_full_name="acme/api",
            branch_name="develop",
            selected_metrics=["pr_title"],
        )
        assert collector.token == "mytoken"
        assert collector.repo_full_name == "acme/api"
        assert collector.branch_name == "develop"
        assert "pr_title" in collector.selected_metrics

    def test_gitlab_receives_project_id(self):
        collector = FetcherFactory.create(
            platform="gitlab",
            token="t",
            repo_full_name="o/r",
            project_id="42",
        )
        assert collector.project_id == "42"

    def test_base_collector_is_abstract(self):
        """BaseCollector cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseCollector(token="t", repo_full_name="o/r")  # type: ignore


# =============================================================================
# GitHubCollector — unit tests (no real HTTP)
# =============================================================================

class TestGitHubCollector:
    def test_session_has_auth_header(self):
        c = GitHubCollector(token="ghp_test", repo_full_name="o/r")
        assert "Authorization" in c.headers
        assert "ghp_test" in c.headers["Authorization"]

    def test_default_branch_is_none(self):
        c = GitHubCollector(token="t", repo_full_name="o/r")
        assert c.branch_name is None

    @patch("collectors.infrastructure.providers.github_fetcher.GitHubCollector._get_total_pr_count", return_value=0)
    @patch("collectors.infrastructure.providers.github_fetcher.GitHubCollector._get_pull_requests_page", return_value=[])
    def test_collect_all_data_empty_repo(self, _page, _count):
        c = GitHubCollector(token="t", repo_full_name="o/r")
        # Patch the instance session so no real HTTP happens for repo details
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        c.session.get = MagicMock(return_value=mock_resp)
        result = c.collect_all_data()
        assert result == {"pull_requests": [], "project_created_at": None}

    @patch("collectors.infrastructure.providers.github_fetcher.GitHubCollector._get_total_pr_count", return_value=0)
    @patch("collectors.infrastructure.providers.github_fetcher.GitHubCollector._get_pull_requests_page", return_value=[])
    def test_collect_returns_dict_with_pull_requests_key(self, _page, _count):
        c = GitHubCollector(token="t", repo_full_name="o/r")
        # Patch session.get to avoid real HTTP for repo details
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        c.session.get = MagicMock(return_value=mock_resp)
        result = c.collect_all_data()
        assert "pull_requests" in result


# =============================================================================
# GitLabCollector — unit tests (no real HTTP)
# =============================================================================

class TestGitLabCollector:
    def test_session_has_private_token_header(self):
        c = GitLabCollector(token="glpat_tok", repo_full_name="ns/proj")
        assert "PRIVATE-TOKEN" in c.headers

    def test_accepts_explicit_project_id(self):
        c = GitLabCollector(token="t", repo_full_name="o/r", project_id="99")
        assert c.project_id == "99"

    @patch("collectors.infrastructure.providers.gitlab_fetcher.GitLabCollector._get_project_id", return_value="1")
    @patch("collectors.infrastructure.providers.gitlab_fetcher.GitLabCollector._get_total_mr_count", return_value=0)
    @patch("collectors.infrastructure.providers.gitlab_fetcher.GitLabCollector._get_merge_requests_page", return_value=[])
    def test_collect_all_data_empty_repo(self, _page, _count, _pid):
        c = GitLabCollector(token="t", repo_full_name="o/r")
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        c.session.get = MagicMock(return_value=mock_resp)
        result = c.collect_all_data()
        assert "merge_requests" in result


# =============================================================================
# MinIOClient — all I/O mocked
# =============================================================================

class TestMinIOClient:
    @patch("collectors.infrastructure.storage.minio_client.Minio")
    def test_generate_filename_format(self, mock_minio_cls):
        mock_client = MagicMock()
        mock_client.bucket_exists.return_value = True
        mock_minio_cls.return_value = mock_client

        from collectors.infrastructure.storage.minio_client import MinIOClient
        client = MinIOClient()
        fname = client.generate_filename("my-repo", 7, "json")
        assert fname.startswith("my-repo_collection7_")
        assert fname.endswith(".json")

    @patch("collectors.infrastructure.storage.minio_client.Minio")
    def test_save_and_get_json(self, mock_minio_cls):
        import json

        stored = {}

        def fake_put(bucket, filename, stream, **kwargs):
            stored[filename] = stream.read()

        def fake_get(bucket, filename):
            r = MagicMock()
            r.read.return_value = stored[filename]
            return r

        mock_client = MagicMock()
        mock_client.bucket_exists.return_value = True
        mock_client.put_object.side_effect = fake_put
        mock_client.get_object.side_effect = fake_get
        mock_minio_cls.return_value = mock_client

        from collectors.infrastructure.storage.minio_client import MinIOClient
        c = MinIOClient()

        payload = {"pull_requests": [{"id": 1}]}
        assert c.save_json(payload, "test.json") is True
        result = c.get_json("test.json")
        assert result == payload

    @patch("collectors.infrastructure.storage.minio_client.Minio")
    def test_delete_file(self, mock_minio_cls):
        mock_client = MagicMock()
        mock_client.bucket_exists.return_value = True
        mock_minio_cls.return_value = mock_client

        from collectors.infrastructure.storage.minio_client import MinIOClient
        c = MinIOClient()
        result = c.delete_file("file.json")
        assert result is True
        mock_client.remove_object.assert_called_once()


# =============================================================================
# BranchFetcher — routing
# =============================================================================

class TestBranchFetcher:
    def test_github_headers(self):
        bf = BranchFetcher(platform="github", token="ghp_x", repo_full_name="o/r")
        assert "Authorization" in bf.headers

    def test_gitlab_headers(self):
        bf = BranchFetcher(platform="gitlab", token="glp_x", repo_full_name="o/r")
        assert "PRIVATE-TOKEN" in bf.headers

    @patch("collectors.infrastructure.providers.branch_fetcher.requests.get")
    def test_fetch_github_branches_success(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [
            {"name": "main", "commit": {"sha": "abc"}, "protected": False}
        ]
        mock_get.return_value = mock_resp

        bf = BranchFetcher(platform="github", token="t", repo_full_name="o/r")
        branches = bf._fetch_github_branches()
        assert len(branches) == 1
        assert branches[0]["name"] == "main"

    @patch("collectors.infrastructure.providers.branch_fetcher.requests.get")
    def test_fetch_branches_returns_empty_on_error(self, mock_get):
        mock_get.side_effect = Exception("network error")
        bf = BranchFetcher(platform="github", token="t", repo_full_name="o/r")
        branches = bf.fetch_branches()
        assert branches == []
