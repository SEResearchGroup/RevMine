from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import UUID

import pandas as pd
import pytest

from analytics.infrastructure.tasks import devops_tasks as tasks


class FakeJob(SimpleNamespace):
    def save(self, update_fields=None):
        self.saved_fields = update_fields

    def refresh_from_db(self):
        self.refreshed = True


def make_job(**kwargs):
    defaults = {
        "id": UUID("00000000-0000-0000-0000-000000000001"),
        "source_type": "kanban",
        "provider": "github",
        "label": "Board",
        "request_payload": {"provider": "github", "board_id": "board-1"},
        "workspace_id": 4,
        "repository_id": 8,
        "user_id": 12,
        "collected_items": 0,
    }
    defaults.update(kwargs)
    return FakeJob(**defaults)


@patch("analytics.infrastructure.tasks.devops_tasks.threading.Thread")
def test_start_job_spawns_daemon_thread(mock_thread_cls):
    thread = MagicMock()
    mock_thread_cls.return_value = thread
    job = make_job()

    tasks.start_job(job, "tok")

    mock_thread_cls.assert_called_once()
    assert mock_thread_cls.call_args.kwargs["target"] is tasks._run_job
    assert mock_thread_cls.call_args.kwargs["args"] == (str(job.id), "tok")
    assert mock_thread_cls.call_args.kwargs["daemon"] is True
    thread.start.assert_called_once()


def test_set_progress_clamps_and_truncates_message():
    job = make_job()
    tasks._set_progress(job, 120, "x" * 300)

    assert job.progress_percent == 100
    assert len(job.progress_message) == 255
    assert job.saved_fields == ["progress_percent", "progress_message"]

    tasks._set_progress(job, -5, "low")
    assert job.progress_percent == 0


def test_filename_and_source_config_for_supported_sources():
    kanban = make_job(source_type="kanban", provider="gitlab", label="Fallback", request_payload={"name": "Sprint", "provider": "gitlab"})
    cicd = make_job(source_type="cicd", provider="github", request_payload={"repo_full_name": "owner/repo", "workspace_id": 4})
    other = make_job(source_type="custom", provider="github", label="Custom", request_payload={})

    assert tasks._filename_for_job(kanban, kanban.request_payload) == "kanban_gitlab_Sprint.csv"
    assert tasks._filename_for_job(cicd, cicd.request_payload) == "cicd_github_Board.csv"
    assert tasks._filename_for_job(other, other.request_payload) == "custom_Custom.csv"
    assert tasks._source_config_for_job(cicd, cicd.request_payload) == {
        "provider": "github",
        "repo_full_name": "owner/repo",
        "workspace_id": 4,
    }


@patch("analytics.infrastructure.tasks.devops_tasks.GitHubProjectsCollector")
def test_run_kanban_github_uses_projects_collector(mock_collector_cls):
    job = make_job(request_payload={"provider": "github", "board_id": "board-1"})
    mock_collector_cls.return_value.collect_board.return_value = pd.DataFrame([{"id": 1}])

    df = tasks._run_kanban(job, "tok")

    assert len(df) == 1
    mock_collector_cls.assert_called_once_with("tok")
    mock_collector_cls.return_value.collect_board.assert_called_once_with("board-1")


@patch("analytics.infrastructure.tasks.devops_tasks.GitLabBoardsCollector")
def test_run_kanban_gitlab_requires_project_and_uses_base_url(mock_collector_cls):
    job = make_job(
        provider="gitlab",
        request_payload={"provider": "gitlab", "board_id": "board-1", "project_id": 42, "base_url": "https://gitlab.test"},
    )
    mock_collector_cls.return_value.collect.return_value = pd.DataFrame([{"id": 1}])

    df = tasks._run_kanban(job, "tok")

    assert len(df) == 1
    mock_collector_cls.assert_called_once_with("tok", 42, "https://gitlab.test")


def test_run_kanban_rejects_unsupported_provider():
    job = make_job(provider="bitbucket", request_payload={"provider": "bitbucket", "board_id": "1"})

    with pytest.raises(ValueError, match="Unsupported provider"):
        tasks._run_kanban(job, "tok")


@patch("analytics.infrastructure.tasks.devops_tasks.GitHubActionsCollector")
def test_run_cicd_github_requires_repo_and_passes_limits(mock_collector_cls):
    job = make_job(
        source_type="cicd",
        provider="github",
        request_payload={"provider": "github", "repo_full_name": "owner/repo", "since": "2024-01-01", "max_runs": "25"},
    )
    mock_collector_cls.return_value.collect.return_value = pd.DataFrame([{"id": 1}])

    df = tasks._run_cicd(job, "tok")

    assert len(df) == 1
    mock_collector_cls.assert_called_once_with("tok", "owner/repo")
    mock_collector_cls.return_value.collect.assert_called_once_with(since="2024-01-01", max_runs=25)


@patch("analytics.infrastructure.tasks.devops_tasks.GitLabCICollector")
def test_run_cicd_gitlab_requires_project_and_uses_defaults(mock_collector_cls):
    job = make_job(source_type="cicd", provider="gitlab", request_payload={"provider": "gitlab", "project_id": 42})
    mock_collector_cls.return_value.collect.return_value = pd.DataFrame([{"id": 1}])

    df = tasks._run_cicd(job, "tok")

    assert len(df) == 1
    mock_collector_cls.assert_called_once_with("tok", 42, "https://gitlab.com")
    mock_collector_cls.return_value.collect.assert_called_once_with(max_pipelines=300)


@pytest.mark.parametrize(
    ("job", "message"),
    [
        (make_job(source_type="cicd", provider="github", request_payload={"provider": "github"}), "repo_full_name"),
        (make_job(source_type="cicd", provider="gitlab", request_payload={"provider": "gitlab"}), "project_id"),
        (make_job(source_type="cicd", provider="unknown", request_payload={"provider": "unknown"}), "Unsupported provider"),
    ],
)
def test_run_cicd_validation_errors(job, message):
    with pytest.raises(ValueError, match=message):
        tasks._run_cicd(job, "tok")


def test_publish_notification_skips_missing_user_and_missing_kafka(monkeypatch):
    tasks._publish_notification(make_job(user_id=0), "started")

    with patch.dict("sys.modules", {"kafka_utils.client": None}):
        tasks._publish_notification(make_job(), "started")


def test_publish_notification_builds_phase_payloads(monkeypatch):
    published = []

    class FakeKafkaClient:
        @staticmethod
        def publish(topic, payload):
            published.append((topic, payload))

    class FakeTopics:
        NOTIFICATION_EVENTS = "notification.events"

    monkeypatch.setitem(__import__("sys").modules, "kafka_utils.client", SimpleNamespace(KafkaClient=FakeKafkaClient))
    monkeypatch.setitem(__import__("sys").modules, "kafka_utils.topics", SimpleNamespace(Topics=FakeTopics))

    job = make_job(source_type="cicd", provider="github", collected_items=5)
    dataset = SimpleNamespace(id="dataset-1")

    tasks._publish_notification(job, "started")
    tasks._publish_notification(job, "completed", dataset=dataset)
    tasks._publish_notification(job, "failed", error="offline")

    assert [payload["type"] for _, payload in published] == [
        "devops_cicd_started",
        "devops_cicd_completed",
        "devops_cicd_failed",
    ]
    assert published[1][1]["link_url"] == "cicd/dataset-1/collect-metrics"
    assert "offline" in published[2][1]["message"]


def test_run_job_returns_when_job_not_found():
    with patch.object(tasks.DevOpsCollectionJob.objects, "filter") as mock_filter:
        mock_filter.return_value.first.return_value = None

        tasks._run_job(str(make_job().id), "tok")

        mock_filter.assert_called_once()


@patch("analytics.infrastructure.tasks.devops_tasks.DatasetService")
@patch("analytics.infrastructure.tasks.devops_tasks._run_kanban")
@patch("analytics.infrastructure.tasks.devops_tasks._publish_notification")
def test_run_job_success_updates_job_and_creates_dataset(mock_publish, mock_run_kanban, mock_dataset_service):
    job = make_job()
    mock_run_kanban.return_value = pd.DataFrame([{"id": 1}, {"id": 2}])
    dataset = SimpleNamespace(id="dataset-1", rows_count=2)
    mock_dataset_service.return_value.create_dataset_from_dataframe.return_value = dataset

    with patch.object(tasks.DevOpsCollectionJob.objects, "filter") as mock_filter:
        mock_filter.return_value.first.return_value = job
        tasks._run_job(str(job.id), "tok")

    assert job.status == "completed"
    assert job.dataset is dataset
    assert job.collected_items == 2
    assert job.total_items == 2
    assert job.progress_percent == 100
    mock_publish.assert_any_call(job, "started")
    mock_publish.assert_any_call(job, "completed", dataset=dataset)


@patch("analytics.infrastructure.tasks.devops_tasks._run_cicd", return_value=pd.DataFrame())
@patch("analytics.infrastructure.tasks.devops_tasks._publish_notification")
def test_run_job_failure_marks_failed_and_notifies(mock_publish, _mock_run_cicd):
    job = make_job(source_type="cicd", provider="github", request_payload={"provider": "github", "repo_full_name": "owner/repo"})

    with patch.object(tasks.DevOpsCollectionJob.objects, "filter") as mock_filter:
        mock_filter.return_value.first.return_value = job
        tasks._run_job(str(job.id), "tok")

    assert job.status == "failed"
    assert job.error_message == "Provider returned no rows."
    mock_publish.assert_any_call(job, "failed", error="Provider returned no rows.")


@patch("analytics.infrastructure.tasks.devops_tasks._publish_notification")
def test_run_job_unknown_source_type_marks_failed(mock_publish):
    job = make_job(source_type="unknown")

    with patch.object(tasks.DevOpsCollectionJob.objects, "filter") as mock_filter:
        mock_filter.return_value.first.return_value = job
        tasks._run_job(str(job.id), "tok")

    assert job.status == "failed"
    assert "Unsupported source_type" in job.error_message
    mock_publish.assert_any_call(job, "failed", error=job.error_message)
