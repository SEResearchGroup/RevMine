from unittest.mock import MagicMock

import pandas as pd

from analytics.infrastructure.collectors import devops_collectors as dc


class ResponseStub:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload
        self.raise_for_status = MagicMock()

    def json(self):
        return self._payload


def test_github_actions_collects_runs_and_jobs(monkeypatch):
    collector = dc.GitHubActionsCollector("tok", "owner/repo")
    collector._iter_runs = MagicMock(
        return_value=iter(
            [
                {
                    "id": 10,
                    "name": "CI",
                    "conclusion": "success",
                    "status": "completed",
                    "head_branch": "main",
                    "head_sha": "abc",
                    "actor": {"login": "alice"},
                    "created_at": "2024-01-01T00:00:00Z",
                    "run_started_at": "2024-01-01T00:01:00Z",
                    "updated_at": "2024-01-01T00:03:00Z",
                }
            ]
        )
    )
    collector._iter_jobs_for_run = MagicMock(
        return_value=iter(
            [
                {
                    "id": 20,
                    "name": "test",
                    "status": "completed",
                    "conclusion": "success",
                    "runner_name": "runner-1",
                    "created_at": "2024-01-01T00:01:00Z",
                    "started_at": "2024-01-01T00:02:00Z",
                    "completed_at": "2024-01-01T00:03:00Z",
                }
            ]
        )
    )

    df = collector.collect(max_runs=1)

    assert df.to_dict("records")[0]["duration_s"] == 120.0
    assert df.to_dict("records")[0]["actor"] == "alice"


def test_github_actions_iterators_stop_on_empty_or_non_200():
    collector = dc.GitHubActionsCollector("tok", "owner/repo")
    collector.session.get = MagicMock(return_value=ResponseStub(200, {"workflow_runs": []}))
    assert list(collector._iter_runs()) == []

    collector.session.get = MagicMock(return_value=ResponseStub(503, {"jobs": [{"id": 1}]}))
    assert list(collector._iter_jobs_for_run(10)) == []


def test_github_actions_list_workflows_and_paginated_iterators():
    collector = dc.GitHubActionsCollector("tok", "owner/repo")
    first_runs = [{"id": i} for i in range(100)]
    second_runs = [{"id": 101}]
    first_jobs = [{"id": i} for i in range(100)]
    second_jobs = [{"id": 101}]
    collector.session.get = MagicMock(
        side_effect=[
            ResponseStub(200, {"workflows": [{"id": 1, "name": "CI"}]}),
            ResponseStub(200, {"workflow_runs": first_runs}),
            ResponseStub(200, {"workflow_runs": second_runs}),
            ResponseStub(200, {"jobs": first_jobs}),
            ResponseStub(200, {"jobs": second_jobs}),
        ]
    )

    assert collector.list_workflows() == [{"id": 1, "name": "CI"}]
    assert [run["id"] for run in collector._iter_runs(since="2024-01-01")][-1] == 101
    assert [job["id"] for job in collector._iter_jobs_for_run(10)][-1] == 101
    assert collector.session.get.call_args_list[1].kwargs["params"]["created"] == ">2024-01-01"


def test_github_actions_collect_handles_bad_duration_and_max_run_break():
    collector = dc.GitHubActionsCollector("tok", "owner/repo")
    collector._iter_runs = MagicMock(
        return_value=iter(
            [
                {"id": 1, "name": "CI", "created_at": "bad", "updated_at": "also-bad"},
                {"id": 2, "name": "CI"},
            ]
        )
    )
    collector._iter_jobs_for_run = MagicMock(return_value=iter([{"id": 10, "name": "test"}]))

    df = collector.collect(max_runs=1)

    assert len(df) == 1
    assert pd.isna(df.iloc[0]["duration_s"])
    collector._iter_jobs_for_run.assert_called_once_with(1)


def test_github_projects_list_projects_and_collect_board(monkeypatch):
    collector = dc.GitHubProjectsCollector("tok")
    collector._graphql = MagicMock(
        side_effect=[
            {
                "user": {"projectsV2": {"nodes": [{"id": "u1", "number": 1, "title": "User board"}]}},
                "organization": {"projectsV2": {"nodes": [{"id": "o1", "number": 2, "title": "Org board"}]}},
            },
            {
                "node": {
                    "items": {
                        "nodes": [
                            {
                                "id": "item-1",
                                "createdAt": "2024-01-01T00:00:00Z",
                                "content": {
                                    "title": "Issue",
                                    "state": "OPEN",
                                    "createdAt": "2024-01-01T00:00:00Z",
                                    "closedAt": "2024-01-02T00:00:00Z",
                                    "author": {"login": "alice"},
                                    "assignees": {"nodes": [{"login": "bob"}]},
                                    "labels": {"nodes": [{"name": "bug"}]},
                                },
                                "fieldValues": {
                                    "nodes": [
                                        {"name": "Done", "field": {"name": "Status"}},
                                    ]
                                },
                            }
                        ],
                        "pageInfo": {"hasNextPage": False},
                    }
                }
            },
        ]
    )

    assert [p["id"] for p in collector.list_projects("acme")] == ["u1", "o1"]
    df = collector.collect_board("project-node")

    row = df.to_dict("records")[0]
    assert row["column"] == "Done"
    assert row["assignee"] == "bob"
    assert row["duration_h"] == 24


def test_github_projects_graphql_raises_on_errors_and_collects_multiple_pages():
    collector = dc.GitHubProjectsCollector("tok")
    collector.session.post = MagicMock(return_value=ResponseStub(200, {"errors": [{"message": "bad"}]}))

    try:
        collector._graphql("query", {})
        raised = False
    except RuntimeError:
        raised = True
    assert raised is True

    collector._graphql = MagicMock(
        side_effect=[
            {
                "node": {
                    "items": {
                        "nodes": [{"id": "1", "content": {"state": "OPEN"}, "fieldValues": {"nodes": []}}],
                        "pageInfo": {"hasNextPage": True, "endCursor": "next"},
                    }
                }
            },
            {
                "node": {
                    "items": {
                        "nodes": [{"id": "2", "content": {"state": "DONE"}, "fieldValues": {"nodes": []}}],
                        "pageInfo": {"hasNextPage": False},
                    }
                }
            },
        ]
    )

    df = collector.collect_board("project")

    assert df["issue_id"].tolist() == ["1", "2"]
    assert collector._graphql.call_args_list[1].args[1]["cursor"] == "next"


def test_github_projects_list_returns_empty_on_graphql_failure():
    collector = dc.GitHubProjectsCollector("tok")
    collector._graphql = MagicMock(side_effect=RuntimeError("forbidden"))

    assert collector.list_projects("acme") == []


def test_gitlab_ci_collects_pipeline_jobs_and_limits_pages():
    collector = dc.GitLabCICollector("tok", project_id=42, base_url="https://gitlab.example.com/")
    collector.list_pipelines_page = MagicMock(
        return_value=[
            {"id": 1, "ref": "main", "sha": "abc", "name": "pipeline"},
            {"id": 2, "ref": "main", "sha": "def", "name": "pipeline"},
        ]
    )
    collector._iter_jobs = MagicMock(
        return_value=iter(
            [
                {
                    "id": 11,
                    "name": "build",
                    "stage": "test",
                    "status": "success",
                    "user": {"username": "alice"},
                    "runner": {"description": "runner"},
                    "duration": 3.5,
                    "created_at": "2024-01-01T00:00:00Z",
                    "finished_at": "2024-01-01T00:00:04Z",
                }
            ]
        )
    )

    df = collector.collect(max_pipelines=1)

    assert len(df) == 1
    assert df.iloc[0]["duration_s"] == 3.5
    assert collector._url("/pipelines").endswith("/api/v4/projects/42/pipelines")


def test_gitlab_ci_iter_jobs_stops_on_non_200_and_empty_page():
    collector = dc.GitLabCICollector("tok", project_id=42)
    collector.session.get = MagicMock(return_value=ResponseStub(500, []))
    assert list(collector._iter_jobs(1)) == []

    collector.session.get = MagicMock(return_value=ResponseStub(200, []))
    assert list(collector._iter_jobs(1)) == []


def test_gitlab_ci_list_page_and_paginated_collect():
    collector = dc.GitLabCICollector("tok", project_id=42)
    first_jobs = [{"id": i, "status": "success"} for i in range(100)]
    second_jobs = [{"id": 101, "status": "failed", "duration": None}]
    collector.session.get = MagicMock(
        side_effect=[
            ResponseStub(200, [{"id": 1, "ref": "main", "sha": "abc"}]),
            ResponseStub(200, first_jobs),
            ResponseStub(200, second_jobs),
        ]
    )

    assert collector.list_pipelines_page(page=2, per_page=10) == [{"id": 1, "ref": "main", "sha": "abc"}]
    jobs = list(collector._iter_jobs(1))
    assert len(jobs) == 101

    collector.list_pipelines_page = MagicMock(side_effect=[[{"id": 1}], []])
    collector._iter_jobs = MagicMock(return_value=iter([{"id": 10, "status": "success"}]))
    df = collector.collect(max_pipelines=300)
    assert len(df) == 1


def test_gitlab_boards_collects_issue_rows_and_column_labels():
    collector = dc.GitLabBoardsCollector("tok", project_id=42)
    collector._iter_issues = MagicMock(
        return_value=iter(
            [
                {
                    "id": 7,
                    "title": "Fix bug",
                    "state": "closed",
                    "created_at": "2024-01-01T00:00:00Z",
                    "closed_at": "2024-01-01T12:00:00Z",
                    "labels": ["workflow::review", "bug"],
                    "assignee": {"username": "bob"},
                    "author": {"username": "alice"},
                }
            ]
        )
    )

    df = collector.collect()

    assert df.iloc[0]["column"] == "workflow::review"
    assert df.iloc[0]["duration_h"] == 12
    assert df.iloc[0]["labels"] == "workflow::review,bug"


def test_gitlab_boards_list_and_iter_issues_branches():
    collector = dc.GitLabBoardsCollector("tok", project_id=42, base_url="https://gitlab.example.com/")
    issues = [{"id": i, "title": f"Issue {i}"} for i in range(100)]
    collector.session.get = MagicMock(
        side_effect=[
            ResponseStub(200, [{"id": 1, "name": "Board"}]),
            ResponseStub(200, issues),
            ResponseStub(200, []),
            ResponseStub(500, []),
        ]
    )

    assert collector.list_boards() == [{"id": 1, "name": "Board"}]
    assert len(list(collector._iter_issues())) == 100
    assert list(collector._iter_issues()) == []
    assert collector._url("/issues").endswith("/api/v4/projects/42/issues")


def test_gitlab_boards_collect_handles_invalid_duration_and_wip_label():
    collector = dc.GitLabBoardsCollector("tok", project_id=42)
    collector._iter_issues = MagicMock(
        return_value=iter(
            [
                {
                    "id": 8,
                    "title": "Build",
                    "state": "opened",
                    "created_at": "bad",
                    "closed_at": "also-bad",
                    "labels": ["doing now"],
                    "assignee": None,
                    "author": None,
                }
            ]
        )
    )

    df = collector.collect()

    assert df.iloc[0]["column"] == "doing now"
    assert df.iloc[0]["duration_h"] is None


def test_session_installs_retry_adapter(monkeypatch):
    session = dc._session({"Authorization": "token"})

    assert session.headers["Authorization"] == "token"
    assert "https://" in session.adapters
