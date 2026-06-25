"""Unit tests for the infrastructure layer.

Tests cover:
- MinIOClient behaviour (storage)
- FetcherFactory instantiation
- GitHubCollector / GitLabCollector session creation
- BranchFetcher routing
"""
import pytest
import requests
from datetime import date
from unittest.mock import MagicMock, patch, PropertyMock

from collectors.factories.fetcher_factory import FetcherFactory
from collectors.infrastructure.providers.github_fetcher import GitHubCollector
from collectors.infrastructure.providers.gitlab_fetcher import (
    GitLabCollector,
    _create_session as create_gitlab_session,
)
from collectors.infrastructure.providers.branch_fetcher import BranchFetcher
from collectors.infrastructure.providers.base import BaseCollector


class ResponseStub:
    def __init__(self, status_code=200, payload=None, headers=None, text=""):
        self.status_code = status_code
        self._payload = payload
        self.headers = headers or {}
        self.text = text

    def json(self):
        return self._payload


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

    def test_get_total_pr_count_graphql_without_filters(self):
        c = GitHubCollector(token="t", repo_full_name="owner/repo")
        response = ResponseStub(
            payload={
                "data": {
                    "repository": {
                        "pullRequests": {
                            "totalCount": 42,
                        }
                    }
                }
            }
        )
        c.session.post = MagicMock(return_value=response)

        assert c._get_total_pr_count_graphql() == 42
        sent = c.session.post.call_args.kwargs["json"]
        assert sent["variables"] == {"owner": "owner", "name": "repo"}

    def test_get_total_pr_count_graphql_with_filters_and_branch(self):
        c = GitHubCollector(token="t", repo_full_name="owner/repo", branch_name="main")
        response = ResponseStub(payload={"data": {"search": {"issueCount": 7}}})
        c.session.post = MagicMock(return_value=response)

        result = c._get_total_pr_count_graphql(
            {"start_date": date(2024, 1, 1), "end_date": date(2024, 1, 31)}
        )

        assert result == 7
        variables = c.session.post.call_args.kwargs["json"]["variables"]
        assert "base:main" in variables["searchQuery"]
        assert "created:2024-01-01..2024-01-31" in variables["searchQuery"]

    def test_get_total_pr_count_falls_back_when_graphql_fails(self):
        c = GitHubCollector(token="t", repo_full_name="owner/repo")
        c._get_total_pr_count_graphql = MagicMock(side_effect=Exception("graphql down"))
        c._get_total_pr_count_link_header = MagicMock(return_value=5)

        assert c._get_total_pr_count() == 5
        c._get_total_pr_count_link_header.assert_called_once()

    def test_get_total_pr_count_link_header_last_page(self):
        c = GitHubCollector(token="t", repo_full_name="owner/repo", branch_name="main")
        c.session.get = MagicMock(
            return_value=ResponseStub(
                payload=[{"number": 1}],
                headers={
                    "Link": '<https://api.github.com/repositories/1/pulls?page=12>; rel="last"'
                },
            )
        )

        assert c._get_total_pr_count_link_header() == 12
        assert c.session.get.call_args.kwargs["params"]["base"] == "main"

    def test_get_total_pr_count_link_header_uses_page_length_without_link(self):
        c = GitHubCollector(token="t", repo_full_name="owner/repo")
        c.session.get = MagicMock(return_value=ResponseStub(payload=[{"number": 1}, {"number": 2}]))

        assert c._get_total_pr_count_link_header() == 2

    def test_get_total_pr_count_link_header_returns_zero_on_error(self):
        c = GitHubCollector(token="t", repo_full_name="owner/repo")
        c.session.get = MagicMock(side_effect=RuntimeError("boom"))

        assert c._get_total_pr_count_link_header() == 0

    @pytest.mark.parametrize(
        ("status_code", "message"),
        [
            (401, "token invalid"),
            (404, "Repository not found"),
            (503, "GitHub API error"),
        ],
    )
    def test_get_pull_requests_page_http_errors(self, status_code, message):
        c = GitHubCollector(token="t", repo_full_name="owner/repo")
        c.session.get = MagicMock(return_value=ResponseStub(status_code=status_code, payload={}))

        with pytest.raises(Exception, match=message):
            c._get_pull_requests_page(1)

    def test_get_pull_requests_page_wraps_timeout(self):
        c = GitHubCollector(token="t", repo_full_name="owner/repo")
        c.session.get = MagicMock(side_effect=requests.exceptions.Timeout("slow"))

        with pytest.raises(Exception, match="Request timeout"):
            c._get_pull_requests_page(1)

    def test_process_pull_request_collects_only_required_endpoints(self):
        c = GitHubCollector(token="t", repo_full_name="owner/repo")
        c.required_endpoints = {"comments", "files"}
        c.session.get = MagicMock(
            side_effect=[
                ResponseStub(payload={"number": 7, "title": "PR"}),
                ResponseStub(payload=[{"body": "hello"}]),
                ResponseStub(payload=[{"filename": "app.py"}]),
            ]
        )

        result = c._process_pull_request(7)

        assert result["details"]["title"] == "PR"
        assert result["comments"] == [{"body": "hello"}]
        assert result["files"] == [{"filename": "app.py"}]
        assert result["commits"] == []
        assert result["reviews"] == []
        assert c.session.get.call_count == 3

    def test_process_pull_request_wraps_endpoint_network_error(self):
        c = GitHubCollector(token="t", repo_full_name="owner/repo")
        c.required_endpoints = {"comments"}
        c.session.get = MagicMock(
            side_effect=[
                ResponseStub(payload={"number": 7}),
                requests.exceptions.ConnectionError("lost"),
            ]
        )

        with pytest.raises(Exception, match="Network error fetching comments"):
            c._process_pull_request(7)

    def test_normalize_review_thread_shapes_node(self):
        node = {
            "id": "PRRT_1",
            "isResolved": True,
            "isOutdated": False,
            "path": "src/x.py",
            "line": 42,
            "originalLine": 40,
            "diffSide": "RIGHT",
            "comments": {"nodes": [
                {
                    "databaseId": 111,
                    "body": "why mutex?",
                    "diffHunk": "@@ -1 +1 @@",
                    "path": "src/x.py",
                    "line": 42,
                    "originalLine": 40,
                    "createdAt": "2026-01-11T10:05:00Z",
                    "updatedAt": "2026-01-11T10:05:00Z",
                    "author": {"__typename": "User", "login": "bob"},
                    "replyTo": None,
                    "pullRequestReview": {"databaseId": 555},
                    "reactions": {"nodes": [{"content": "THUMBS_UP", "user": {"login": "carol"}}]},
                },
                {
                    "databaseId": 112,
                    "body": "because recursion",
                    "diffHunk": "@@ -1 +1 @@",
                    "path": "src/x.py",
                    "line": 42,
                    "originalLine": 40,
                    "createdAt": "2026-01-11T11:00:00Z",
                    "updatedAt": "2026-01-11T11:00:00Z",
                    "author": {"__typename": "Bot", "login": "dependabot"},
                    "replyTo": {"databaseId": 111},
                    "pullRequestReview": None,
                    "reactions": {"nodes": []},
                },
            ]},
        }
        thread = GitHubCollector._normalize_review_thread(node)
        assert thread["is_resolved"] is True
        assert thread["is_outdated"] is False
        assert thread["side"] == "RIGHT"
        assert len(thread["comments"]) == 2
        first = thread["comments"][0]
        assert first["id"] == 111
        assert first["author"] == "bob"
        assert first["author_is_bot"] is False
        assert first["review_id"] == 555
        assert first["reply_to_id"] is None
        assert first["reactions"] == [{"content": "THUMBS_UP", "user": "carol"}]
        second = thread["comments"][1]
        assert second["author_is_bot"] is True
        assert second["reply_to_id"] == 111

    def test_collect_review_threads_parses_single_page(self):
        c = GitHubCollector(token="t", repo_full_name="owner/repo")
        payload = {"data": {"repository": {"pullRequest": {"reviewThreads": {
            "pageInfo": {"hasNextPage": False, "endCursor": None},
            "nodes": [{
                "id": "PRRT_1", "isResolved": False, "isOutdated": False,
                "path": "a.py", "line": 1, "originalLine": 1, "diffSide": "RIGHT",
                "comments": {"nodes": []},
            }],
        }}}}}
        c.session.post = MagicMock(return_value=ResponseStub(payload=payload))
        threads = c._collect_review_threads(7)
        assert len(threads) == 1
        assert threads[0]["id"] == "PRRT_1"

    def test_collect_review_threads_returns_empty_on_graphql_errors(self):
        c = GitHubCollector(token="t", repo_full_name="owner/repo")
        c.session.post = MagicMock(
            return_value=ResponseStub(payload={"errors": [{"message": "bad"}]})
        )
        assert c._collect_review_threads(7) == []

    def test_review_threads_query_stays_under_github_node_limit(self):
        """Regression for MAX_NODE_LIMIT_EXCEEDED: nested first: sizes must keep the
        estimated node count well under GitHub's 500,000 cap."""
        import re
        c = GitHubCollector(token="t", repo_full_name="owner/repo")
        captured = {}

        def fake_post(url, json=None, headers=None, timeout=None):
            captured["query"] = json["query"]
            return ResponseStub(payload={"data": {"repository": {"pullRequest": {
                "reviewThreads": {"pageInfo": {"hasNextPage": False, "endCursor": None}, "nodes": []}
            }}}})

        c.session.post = MagicMock(side_effect=fake_post)
        c._collect_review_threads(7)

        firsts = [int(n) for n in re.findall(r"first:\s*(\d+)", captured["query"])]
        assert len(firsts) == 3  # reviewThreads x comments x reactions
        estimate, cum = 0, 1
        for n in firsts:
            cum *= n
            estimate += cum
        assert estimate < 500000

    def test_collect_review_threads_paginates(self):
        c = GitHubCollector(token="t", repo_full_name="owner/repo")

        def node(thread_id):
            return {"id": thread_id, "isResolved": False, "isOutdated": False,
                    "path": "a.py", "line": 1, "originalLine": 1, "diffSide": "RIGHT",
                    "comments": {"nodes": []}}

        page1 = {"data": {"repository": {"pullRequest": {"reviewThreads": {
            "pageInfo": {"hasNextPage": True, "endCursor": "C1"}, "nodes": [node("T1")]}}}}}
        page2 = {"data": {"repository": {"pullRequest": {"reviewThreads": {
            "pageInfo": {"hasNextPage": False, "endCursor": None}, "nodes": [node("T2")]}}}}}
        c.session.post = MagicMock(side_effect=[ResponseStub(payload=page1), ResponseStub(payload=page2)])

        threads = c._collect_review_threads(7)
        assert [t["id"] for t in threads] == ["T1", "T2"]
        assert c.session.post.call_count == 2

    def test_collect_issue_comment_reactions_normalizes(self):
        c = GitHubCollector(token="t", repo_full_name="owner/repo")
        c.session.get = MagicMock(
            return_value=ResponseStub(payload=[{"content": "heart", "user": {"login": "bob"}}])
        )
        assert c._collect_issue_comment_reactions(99) == [{"content": "heart", "user": "bob"}]

    def test_process_pull_request_qualitative_enrichment(self):
        c = GitHubCollector(token="t", repo_full_name="owner/repo")
        # Restrict HTTP endpoints to keep the test focused on the enrichment branch.
        c.required_endpoints = {"comments"}
        c.for_qualitative = True
        c.session.get = MagicMock(
            side_effect=[
                ResponseStub(payload={"number": 7, "title": "PR"}),  # details
                ResponseStub(payload=[{"id": 1, "body": "hi"}]),      # comments
            ]
        )
        c._collect_review_threads = MagicMock(return_value=[{"id": "PRRT_1"}])
        c._collect_issue_comment_reactions = MagicMock(
            return_value=[{"content": "heart", "user": "bob"}]
        )

        result = c._process_pull_request(7)

        assert result["review_threads"] == [{"id": "PRRT_1"}]
        assert result["comments"][0]["reactions"] == [{"content": "heart", "user": "bob"}]
        c._collect_review_threads.assert_called_once_with(7)
        c._collect_issue_comment_reactions.assert_called_once_with(1)

    def test_process_pull_request_no_enrichment_when_not_qualitative(self):
        c = GitHubCollector(token="t", repo_full_name="owner/repo")
        c.required_endpoints = {"comments"}
        c.for_qualitative = False
        c.session.get = MagicMock(
            side_effect=[
                ResponseStub(payload={"number": 7}),
                ResponseStub(payload=[{"id": 1, "body": "hi"}]),
            ]
        )
        result = c._process_pull_request(7)
        assert "review_threads" not in result
        assert "reactions" not in result["comments"][0]

    @patch("collectors.infrastructure.providers.github_fetcher.GitHubCollector._process_pull_request")
    @patch("collectors.infrastructure.providers.github_fetcher.GitHubCollector._get_pull_requests_page")
    @patch("collectors.infrastructure.providers.github_fetcher.GitHubCollector._get_total_pr_count", return_value=2)
    def test_collect_all_data_skips_existing_filters_dates_and_deduplicates(
        self, _count, page, process
    ):
        c = GitHubCollector(token="t", repo_full_name="owner/repo")
        c.session.get = MagicMock(return_value=ResponseStub(payload={"created_at": "2023-01-01T00:00:00Z"}))
        page.side_effect = [
            [
                {"number": 1, "created_at": "2024-01-05T00:00:00Z"},
                {"number": 2, "created_at": "2023-12-01T00:00:00Z"},
                {"number": 3, "created_at": "2024-01-15T00:00:00Z"},
            ],
            [],
        ]
        process.side_effect = [
            {"pull_request_number": 3, "details": {"number": 3}},
        ]
        progress = MagicMock()

        result = c.collect_all_data(
            filters={"start_date": date(2024, 1, 1), "end_date": date(2024, 1, 31)},
            existing_data={"pull_requests": [{"pull_request_number": 1}]},
            progress_callback=progress,
        )

        assert [pr["pull_request_number"] for pr in result["pull_requests"]] == [1, 3]
        process.assert_called_once_with(3)
        assert progress.call_args_list[-1].args[:3] == (2, 2, "Finalizing...")

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
        assert c.session.verify is True

    def test_session_uses_gitlab_ca_bundle(self, monkeypatch):
        monkeypatch.setenv("GITLAB_CA_BUNDLE", "/etc/ssl/gitlab-ca.pem")
        session = create_gitlab_session({"PRIVATE-TOKEN": "tok"})
        assert session.verify == "/etc/ssl/gitlab-ca.pem"

    def test_session_ignores_disabled_tls_verification(self):
        disabled_verification = bool(0)
        session = create_gitlab_session(
            {"PRIVATE-TOKEN": "tok"},
            verify=disabled_verification,
        )
        assert session.verify is True

    def test_accepts_explicit_project_id(self):
        c = GitLabCollector(token="t", repo_full_name="o/r", project_id="99")
        assert c.project_id == "99"

    def test_get_project_id_success_sets_created_at(self):
        c = GitLabCollector(token="t", repo_full_name="group/proj")
        c.session.get = MagicMock(
            return_value=ResponseStub(payload={"id": 123, "created_at": "2020-01-01T00:00:00Z"})
        )

        assert c._get_project_id() == "123"
        assert c.project_created_at == "2020-01-01T00:00:00Z"

    def test_get_project_id_returns_none_on_error(self):
        c = GitLabCollector(token="t", repo_full_name="group/proj")
        c.session.get = MagicMock(side_effect=RuntimeError("network"))

        assert c._get_project_id() is None

    def test_get_total_mr_count_graphql_with_filters(self):
        c = GitLabCollector(
            token="t",
            repo_full_name="group/proj",
            branch_name="main",
            project_id="1",
        )
        c.session.post = MagicMock(
            return_value=ResponseStub(payload={"data": {"project": {"mergeRequests": {"count": 9}}}})
        )

        result = c._get_total_mr_count_graphql(
            {"start_date": date(2024, 1, 1), "end_date": date(2024, 1, 31), "status": ["merged"]}
        )

        assert result == 9
        variables = c.session.post.call_args.kwargs["json"]["variables"]
        assert variables["fullPath"] == "group/proj"
        assert variables["targetBranches"] == ["main"]
        assert variables["createdAfter"] == "2024-01-01"
        assert variables["createdBefore"] == "2024-01-31"
        assert variables["state"] == "merged"

    def test_get_total_mr_count_falls_back_when_graphql_fails(self):
        c = GitLabCollector(token="t", repo_full_name="group/proj", project_id="1")
        c._get_total_mr_count_graphql = MagicMock(side_effect=Exception("old gitlab"))
        c._get_total_mr_count_rest = MagicMock(return_value=4)

        assert c._get_total_mr_count() == 4

    def test_get_total_mr_count_rest_prefers_x_total(self):
        c = GitLabCollector(token="t", repo_full_name="group/proj", branch_name="main", project_id="1")
        c.session.get = MagicMock(return_value=ResponseStub(payload=[{"iid": 99}], headers={"x-total": "18"}))

        assert c._get_total_mr_count_rest({"status": ["open"], "start_date": date(2024, 1, 1)}) == 18
        params = c.session.get.call_args.kwargs["params"]
        assert params["state"] == "opened"
        assert params["target_branch"] == "main"
        assert params["created_after"] == "2024-01-01"

    def test_get_total_mr_count_rest_uses_latest_iid_without_header(self):
        c = GitLabCollector(token="t", repo_full_name="group/proj", project_id="1")
        c.session.get = MagicMock(return_value=ResponseStub(payload=[{"iid": 77}]))

        assert c._get_total_mr_count_rest() == 77

    @pytest.mark.parametrize(
        ("status_code", "payload", "message"),
        [
            (401, {"error_description": "token revoked"}, "token revoked"),
            (404, {}, "Projet GitLab non trouvé"),
            (500, {}, "Erreur GitLab API"),
        ],
    )
    def test_get_merge_requests_page_http_errors(self, status_code, payload, message):
        c = GitLabCollector(token="t", repo_full_name="group/proj", project_id="1")
        c.session.get = MagicMock(
            return_value=ResponseStub(status_code=status_code, payload=payload, text="server error")
        )

        with pytest.raises(Exception, match=message):
            c._get_merge_requests_page(1)

    def test_get_merge_requests_page_wraps_network_error(self):
        c = GitLabCollector(token="t", repo_full_name="group/proj", project_id="1")
        c.session.get = MagicMock(side_effect=requests.exceptions.Timeout("slow"))

        with pytest.raises(Exception, match="Erreur réseau"):
            c._get_merge_requests_page(1)

    def test_process_merge_request_collects_only_required_endpoints(self):
        c = GitLabCollector(token="t", repo_full_name="group/proj", project_id="1")
        c.required_endpoints = {"notes", "changes"}
        c.session.get = MagicMock(
            side_effect=[
                ResponseStub(payload={"iid": 11, "title": "MR"}),
                ResponseStub(payload=[{"body": "note"}]),
                ResponseStub(payload={"changes": [{"new_path": "app.py"}]}),
            ]
        )

        result = c._process_merge_request(11)

        assert result["details"]["title"] == "MR"
        assert result["notes"] == [{"body": "note"}]
        assert result["changes"] == {"changes": [{"new_path": "app.py"}]}
        assert result["commits"] == []
        assert result["discussions"] == []
        assert c.session.get.call_count == 3

    def test_process_merge_request_wraps_timeout(self):
        c = GitLabCollector(token="t", repo_full_name="group/proj", project_id="1")
        c.session.get = MagicMock(side_effect=requests.exceptions.Timeout("slow"))

        with pytest.raises(Exception, match="Délai d'attente"):
            c._process_merge_request(11)

    def test_normalize_award_emoji_shapes_rows(self):
        c = GitLabCollector(token="t", repo_full_name="group/proj", project_id="1")
        rows = [{"name": "thumbsup", "user": {"username": "bob"}}, {"name": "rocket", "user": None}]
        assert c._normalize_award_emoji(rows) == [
            {"name": "thumbsup", "user": "bob"},
            {"name": "rocket", "user": None},
        ]

    def test_process_merge_request_qualitative_enrichment(self):
        c = GitLabCollector(token="t", repo_full_name="group/proj", project_id="1")
        c.required_endpoints = {"discussions", "notes"}
        c.for_qualitative = True
        c.session.get = MagicMock(
            side_effect=[
                ResponseStub(payload={"iid": 11, "title": "MR"}),  # details
                ResponseStub(payload=[{"id": "d1", "notes": [{"id": 9001, "system": False}]}]),  # discussions
                ResponseStub(payload=[{"id": 9001, "system": False}, {"id": 9002, "system": True}]),  # notes
            ]
        )
        c._collect_mr_award_emoji = MagicMock(return_value=[{"name": "rocket", "user": "bob"}])
        c._collect_note_award_emoji = MagicMock(return_value=[{"name": "thumbsup", "user": "carol"}])

        result = c._process_merge_request(11)

        assert result["award_emoji"] == [{"name": "rocket", "user": "bob"}]
        # discussion note + flat note share id 9001 -> fetched once (cached)
        assert result["discussions"][0]["notes"][0]["award_emoji"] == [{"name": "thumbsup", "user": "carol"}]
        # system note (9002) is skipped
        flat_notes = {n["id"]: n for n in result["notes"]}
        assert "award_emoji" in flat_notes[9001]
        assert "award_emoji" not in flat_notes[9002]
        c._collect_note_award_emoji.assert_called_once_with(11, 9001)

    def test_process_merge_request_no_enrichment_when_not_qualitative(self):
        c = GitLabCollector(token="t", repo_full_name="group/proj", project_id="1")
        c.required_endpoints = {"notes"}
        c.for_qualitative = False
        c.session.get = MagicMock(
            side_effect=[
                ResponseStub(payload={"iid": 11}),
                ResponseStub(payload=[{"id": 9001, "system": False}]),
            ]
        )
        result = c._process_merge_request(11)
        assert "award_emoji" not in result
        assert "award_emoji" not in result["notes"][0]

    def test_get_commit_diff_returns_empty_on_http_error_or_exception(self):
        c = GitLabCollector(token="t", repo_full_name="group/proj", project_id="1")
        c.session.get = MagicMock(return_value=ResponseStub(status_code=404, payload=[]))
        assert c._get_commit_diff("abc") == []

        c.session.get = MagicMock(side_effect=RuntimeError("boom"))
        assert c._get_commit_diff("abc") == []

    def test_collect_all_data_raises_when_project_id_unresolved(self):
        c = GitLabCollector(token="t", repo_full_name="group/proj")
        c._get_project_id = MagicMock(return_value=None)

        with pytest.raises(Exception, match="Could not get project ID"):
            c.collect_all_data()

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
    @pytest.fixture(autouse=True)
    def minio_settings(self, settings):
        settings.MINIO_ENDPOINT = "storage.example.invalid"
        settings.MINIO_ACCESS_KEY = "example-access-key"
        settings.MINIO_SECRET_KEY = "example-secret-key"

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

    @patch("collectors.infrastructure.storage.minio_client.Minio")
    def test_creates_bucket_when_missing(self, mock_minio_cls):
        from django.conf import settings

        mock_client = MagicMock()
        mock_client.bucket_exists.return_value = False
        mock_minio_cls.return_value = mock_client

        from collectors.infrastructure.storage.minio_client import MinIOClient

        MinIOClient()

        expected_bucket = (
            getattr(settings, "MINIO_BUCKET_NAME", None)
            or getattr(settings, "MINIO_BUCKET", None)
            or "revmine-collections"
        )
        mock_client.make_bucket.assert_called_once_with(expected_bucket)

    @patch("collectors.infrastructure.storage.minio_client.Minio")
    def test_save_json_returns_false_on_s3_error(self, mock_minio_cls, monkeypatch):
        from collectors.infrastructure.storage import minio_client
        from collectors.infrastructure.storage.minio_client import MinIOClient

        mock_client = MagicMock()
        mock_client.bucket_exists.return_value = True
        mock_client.put_object.side_effect = Exception("s3 down")
        mock_minio_cls.return_value = mock_client
        monkeypatch.setattr(minio_client, "S3Error", Exception)

        assert MinIOClient().save_json({"a": 1}, "a.json") is False

    @patch("collectors.infrastructure.storage.minio_client.Minio")
    def test_get_json_returns_none_and_closes_response_on_s3_error(self, mock_minio_cls, monkeypatch):
        from collectors.infrastructure.storage import minio_client
        from collectors.infrastructure.storage.minio_client import MinIOClient

        mock_client = MagicMock()
        mock_client.bucket_exists.return_value = True
        mock_client.get_object.side_effect = Exception("missing")
        mock_minio_cls.return_value = mock_client
        monkeypatch.setattr(minio_client, "S3Error", Exception)

        assert MinIOClient().get_json("missing.json") is None

    @patch("collectors.infrastructure.storage.minio_client.Minio")
    def test_csv_bytes_stream_and_exists_branches(self, mock_minio_cls):
        from collectors.infrastructure.storage.minio_client import MinIOClient

        stored = {}

        def fake_put(_bucket, filename, stream, **_kwargs):
            stored[filename] = stream.read()

        def fake_get(_bucket, filename):
            response = MagicMock()
            response.read.return_value = stored[filename]
            return response

        mock_client = MagicMock()
        mock_client.bucket_exists.return_value = True
        mock_client.put_object.side_effect = fake_put
        mock_client.get_object.side_effect = fake_get
        mock_minio_cls.return_value = mock_client

        c = MinIOClient()
        assert c.save_csv("a,b\n1,2\n", "data.csv") is True
        assert c.get_csv("data.csv") == "a,b\n1,2\n"
        assert c.get_csv_bytes("data.csv") == b"a,b\n1,2\n"
        assert c.save_stream(io_stream := MagicMock(), "stream.json", 12) is True
        assert io_stream is not None

        mock_client.stat_object.return_value = object()
        assert c.file_exists("data.csv") is True

    @patch("collectors.infrastructure.storage.minio_client.Minio")
    def test_minio_error_branches_return_safe_values(self, mock_minio_cls, monkeypatch):
        from collectors.infrastructure.storage import minio_client
        from collectors.infrastructure.storage.minio_client import MinIOClient

        mock_client = MagicMock()
        mock_client.bucket_exists.side_effect = Exception("bucket down")
        mock_client.get_object.side_effect = Exception("missing")
        mock_client.put_object.side_effect = Exception("write failed")
        mock_client.stat_object.side_effect = Exception("not found")
        mock_client.remove_object.side_effect = Exception("delete failed")
        mock_minio_cls.return_value = mock_client
        monkeypatch.setattr(minio_client, "S3Error", Exception)

        c = MinIOClient()
        assert c.get_json_bytes("raw.json") is None
        assert c.save_csv("a,b\n", "data.csv") is False
        assert c.get_csv("data.csv") is None
        assert c.get_csv_bytes("data.csv") is None
        assert c.file_exists("data.csv") is False
        assert c.save_stream(MagicMock(), "stream.json", 1) is False
        assert c.get_object_stream("stream.json") is None
        assert c.delete_file("data.csv") is False


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
        assert bf.verify_tls is True

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

    @patch("collectors.infrastructure.providers.branch_fetcher.requests.get")
    def test_gitlab_date_range_keeps_tls_verification_enabled(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.side_effect = [
            [{"created_at": "2026-01-02T00:00:00Z"}],
            [{"created_at": "2025-01-01T00:00:00Z"}],
        ]
        mock_get.return_value = mock_resp

        bf = BranchFetcher(platform="gitlab", token="t", repo_full_name="o/r")
        bf._get_gitlab_project_id = MagicMock(return_value="42")

        result = bf._fetch_gitlab_date_range()

        assert result == {
            "first_date": "2025-01-01T00:00:00Z",
            "last_date": "2026-01-02T00:00:00Z",
        }
        assert mock_get.call_count == 2
        assert all(call.kwargs["verify"] is True for call in mock_get.call_args_list)

    def test_gitlab_self_base_url_defaults_to_gitlab_api(self):
        bf = BranchFetcher(platform="gitlab_self", token="t", repo_full_name="o/r")
        assert bf.base_url == "https://gitlab.com/api/v4"

    @patch("collectors.infrastructure.providers.branch_fetcher.requests.get")
    def test_fetch_github_branches_non_200_returns_empty(self, mock_get):
        mock_get.return_value = ResponseStub(status_code=500, payload=[])
        bf = BranchFetcher(platform="github", token="t", repo_full_name="o/r")

        assert bf._fetch_github_branches() == []

    @patch("collectors.infrastructure.providers.branch_fetcher.requests.get")
    def test_fetch_gitlab_branches_success(self, mock_get):
        mock_get.return_value = ResponseStub(
            status_code=200,
            payload=[{"name": "main", "commit": {"id": "abc"}, "protected": True, "default": True}],
        )
        bf = BranchFetcher(platform="gitlab", token="t", repo_full_name="group/repo")
        bf._get_gitlab_project_id = MagicMock(return_value="42")

        assert bf._fetch_gitlab_branches() == [
            {"name": "main", "sha": "abc", "protected": True, "default": True}
        ]

    @patch("collectors.infrastructure.providers.branch_fetcher.requests.get")
    def test_get_gitlab_project_id_success_and_failure(self, mock_get):
        bf = BranchFetcher(platform="gitlab", token="t", repo_full_name="group/repo")
        mock_get.return_value = ResponseStub(status_code=200, payload={"id": 123})
        assert bf._get_gitlab_project_id() == "123"

        mock_get.side_effect = RuntimeError("network")
        assert bf._get_gitlab_project_id() is None

    @patch("collectors.infrastructure.providers.branch_fetcher.requests.get")
    def test_github_date_range_handles_empty_and_exceptions(self, mock_get):
        bf = BranchFetcher(platform="github", token="t", repo_full_name="o/r")
        mock_get.side_effect = [
            ResponseStub(status_code=200, payload=[]),
            RuntimeError("timeout"),
        ]

        assert bf._fetch_github_date_range() == {"first_date": None, "last_date": None}

    def test_fetch_date_range_routes_and_handles_unexpected_errors(self):
        github = BranchFetcher(platform="github", token="t", repo_full_name="o/r")
        github._fetch_github_date_range = MagicMock(return_value={"first_date": "a", "last_date": "b"})
        assert github.fetch_date_range() == {"first_date": "a", "last_date": "b"}

        gitlab = BranchFetcher(platform="gitlab", token="t", repo_full_name="o/r")
        gitlab._fetch_gitlab_date_range = MagicMock(side_effect=RuntimeError("boom"))
        assert gitlab.fetch_date_range() == {"first_date": None, "last_date": None}

    @patch("collectors.infrastructure.providers.branch_fetcher.requests.get")
    def test_gitlab_branches_missing_project_and_http_error(self, mock_get):
        bf = BranchFetcher(platform="gitlab", token="t", repo_full_name="group/repo")
        bf._get_gitlab_project_id = MagicMock(return_value=None)
        assert bf._fetch_gitlab_branches() == []

        bf._get_gitlab_project_id = MagicMock(return_value="42")
        mock_get.return_value = ResponseStub(status_code=500, payload=[])
        assert bf._fetch_gitlab_branches() == []

    @patch("collectors.infrastructure.providers.branch_fetcher.requests.get")
    def test_gitlab_date_range_missing_project_and_partial_failures(self, mock_get):
        bf = BranchFetcher(platform="gitlab", token="t", repo_full_name="group/repo")
        bf._get_gitlab_project_id = MagicMock(return_value=None)
        assert bf._fetch_gitlab_date_range() == {"first_date": None, "last_date": None}

        bf._get_gitlab_project_id = MagicMock(return_value="42")
        mock_get.side_effect = [
            RuntimeError("newest failed"),
            ResponseStub(status_code=200, payload=[{"created_at": "2024-01-01T00:00:00Z"}]),
        ]
        assert bf._fetch_gitlab_date_range() == {
            "first_date": "2024-01-01T00:00:00Z",
            "last_date": None,
        }
