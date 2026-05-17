from unittest.mock import MagicMock, patch

import pytest

from collectors.models import Collection
from collectors.tasks import (
    cancellation_registry,
    calculate_statistics,
    execute_collection_task,
    run_collection_in_background,
)


class FakeCollector:
    def __init__(self, data=None, side_effect=None, progress_items=None):
        self.data = data or {"pull_requests": []}
        self.side_effect = side_effect
        self.progress_items = progress_items or []
        self.required_endpoints = None
        self.is_total_approximate = True
        self.call_kwargs = None

    def collect_all_data(self, **kwargs):
        self.call_kwargs = kwargs
        for current, total, item_data, all_data in self.progress_items:
            kwargs["progress_callback"](
                current,
                total,
                message=f"{current}/{total}",
                item_data=item_data,
                all_data=all_data,
            )
        if self.side_effect:
            raise self.side_effect
        return self.data


class TestCancellationRegistry:
    def test_cancel_remove_and_check_are_idempotent(self):
        cancellation_registry.remove(9001)

        cancellation_registry.cancel(9001)
        assert cancellation_registry.is_cancelled(9001) is True

        cancellation_registry.remove(9001)
        assert cancellation_registry.is_cancelled(9001) is False
        cancellation_registry.remove(9001)


def _patch_task_dependencies(fake_collector, mock_minio_cls, mock_factory, mock_kafka):
    minio = MagicMock()
    minio.generate_filename.return_value = "raw.json"
    minio.get_json.return_value = {"pull_requests": [{"details": {"number": 1}}]}
    minio.save_json.return_value = True
    mock_minio_cls.return_value = minio
    mock_factory.create.return_value = fake_collector
    mock_kafka.publish.return_value = None
    return minio


@pytest.mark.django_db
class TestExecuteCollectionTask:
    @patch("collectors.tasks.threading.Thread")
    def test_run_collection_in_background_starts_daemon_thread(self, mock_thread_cls):
        thread = MagicMock()
        mock_thread_cls.return_value = thread

        run_collection_in_background(123, resume=True)

        mock_thread_cls.assert_called_once()
        assert mock_thread_cls.call_args.kwargs["target"] is execute_collection_task
        assert mock_thread_cls.call_args.kwargs["args"] == (123, True)
        assert thread.daemon is True
        thread.start.assert_called_once()

    @patch("collectors.tasks.KafkaClient")
    @patch("collectors.tasks.FetcherFactory")
    @patch("collectors.tasks.MinIOClient")
    def test_cancelled_before_start_skips_collection(self, mock_minio_cls, mock_factory, mock_kafka, create_collection):
        collection = create_collection(status="pending")
        cancellation_registry.cancel(collection.id)

        execute_collection_task(collection.id)

        collection.refresh_from_db()
        assert collection.status == "pending"
        assert cancellation_registry.is_cancelled(collection.id) is False
        mock_factory.create.assert_not_called()
        mock_kafka.publish.assert_not_called()

    @patch("collectors.tasks.get_required_endpoints", return_value={"details", "commits"})
    @patch("collectors.tasks.KafkaClient")
    @patch("collectors.tasks.FetcherFactory")
    @patch("collectors.tasks.MinIOClient")
    def test_successful_github_collection_updates_status_and_saves_json(
        self,
        mock_minio_cls,
        mock_factory,
        mock_kafka,
        mock_required,
        create_collection,
    ):
        collection = create_collection(
            status="pending",
            selected_metrics=["pr_title", "commit_sha"],
            filters={"start_date": "2024-01-01", "end_date": "2024-01-31"},
            save_batch_size=1,
        )
        data = {
            "pull_requests": [
                {
                    "details": {"created_at": "2024-01-15T12:00:00Z"},
                    "commits": [{"sha": "abc"}],
                    "comments": [{"id": 1}],
                    "reviews": [],
                    "review_comments": [],
                }
            ]
        }
        fake_collector = FakeCollector(
            data=data,
            progress_items=[
                (
                    1,
                    1,
                    {"pull_request_number": 7},
                    data,
                )
            ],
        )
        minio = _patch_task_dependencies(fake_collector, mock_minio_cls, mock_factory, mock_kafka)

        execute_collection_task(collection.id)

        collection.refresh_from_db()
        assert collection.status == "completed"
        assert collection.total_items == 1
        assert collection.collected_items == 1
        assert collection.raw_data_filename == "raw.json"
        assert collection.last_collected_item_id == "7"
        assert collection.is_total_approximate is True
        assert collection.stats["pull_requests_count"] == 1
        assert fake_collector.required_endpoints == {"details", "commits"}
        assert fake_collector.call_kwargs["filters"]["start_date"].isoformat() == "2024-01-01"
        assert minio.save_json.call_count == 2
        published_topics = [call.args[0] for call in mock_kafka.publish.call_args_list]
        assert "collection.events.started" in published_topics
        assert "collection.events.completed" in published_topics
        mock_required.assert_called_once_with("github", ["pr_title", "commit_sha"])

    @patch("collectors.tasks.KafkaClient")
    @patch("collectors.tasks.FetcherFactory")
    @patch("collectors.tasks.MinIOClient")
    def test_resume_loads_existing_data_and_resume_marker(
        self,
        mock_minio_cls,
        mock_factory,
        mock_kafka,
        create_collection,
    ):
        collection = create_collection(
            status="paused",
            raw_data_filename="existing.json",
            last_collected_item_id="42",
            selected_metrics=[],
        )
        fake_collector = FakeCollector(data={"merge_requests": []})
        minio = _patch_task_dependencies(fake_collector, mock_minio_cls, mock_factory, mock_kafka)

        execute_collection_task(collection.id, resume=True)

        minio.get_json.assert_called_once_with("existing.json")
        assert fake_collector.call_kwargs["resume_from"] == "42"
        assert fake_collector.call_kwargs["existing_data"] == {"pull_requests": [{"details": {"number": 1}}]}
        collection.refresh_from_db()
        assert collection.status == "completed"

    @patch("collectors.tasks.KafkaClient")
    @patch("collectors.tasks.FetcherFactory")
    @patch("collectors.tasks.MinIOClient")
    def test_collect_failure_without_progress_marks_failed_and_publishes_event(
        self,
        mock_minio_cls,
        mock_factory,
        mock_kafka,
        create_collection,
    ):
        collection = create_collection(
            status="pending",
            selected_metrics=["pr_title"],
            raw_data_filename="raw.json",
        )
        fake_collector = FakeCollector(side_effect=RuntimeError("provider timeout"))
        _patch_task_dependencies(fake_collector, mock_minio_cls, mock_factory, mock_kafka)

        execute_collection_task(collection.id)

        collection.refresh_from_db()
        assert collection.status == "failed"
        assert collection.error_message == "provider timeout"
        published_topics = [call.args[0] for call in mock_kafka.publish.call_args_list]
        assert "collection.events.failed" in published_topics

    @patch("collectors.tasks.KafkaClient")
    @patch("collectors.tasks.FetcherFactory")
    @patch("collectors.tasks.MinIOClient")
    def test_collect_failure_after_progress_marks_paused(
        self,
        mock_minio_cls,
        mock_factory,
        mock_kafka,
        create_collection,
    ):
        collection = create_collection(
            status="pending",
            selected_metrics=["pr_title"],
            raw_data_filename="raw.json",
        )
        fake_collector = FakeCollector(
            side_effect=RuntimeError("network lost"),
            progress_items=[
                (1, 2, {"merge_request_id": 55}, {"merge_requests": [{"details": {}}]})
            ],
        )
        _patch_task_dependencies(fake_collector, mock_minio_cls, mock_factory, mock_kafka)

        execute_collection_task(collection.id)

        collection.refresh_from_db()
        assert collection.status == "paused"
        assert collection.last_collected_item_id == "55"
        assert collection.paused_at is not None

    @patch("collectors.tasks.KafkaClient")
    @patch("collectors.tasks.FetcherFactory")
    @patch("collectors.tasks.MinIOClient")
    def test_collection_deleted_during_progress_cleans_generated_file(
        self,
        mock_minio_cls,
        mock_factory,
        mock_kafka,
        create_collection,
    ):
        collection = create_collection(
            status="pending",
            selected_metrics=["pr_title"],
            raw_data_filename="raw.json",
        )

        def delete_during_refresh(*args, **kwargs):
            Collection.objects.filter(id=collection.id).delete()
            raise Collection.DoesNotExist

        fake_collector = FakeCollector(
            progress_items=[
                (1, 1, {"pull_request_number": 1}, {"pull_requests": [{"details": {}}]})
            ]
        )
        minio = _patch_task_dependencies(fake_collector, mock_minio_cls, mock_factory, mock_kafka)

        with patch.object(Collection, "refresh_from_db", delete_during_refresh):
            execute_collection_task(collection.id)

        minio.delete_file.assert_called_once_with("raw.json")
        assert not Collection.objects.filter(id=collection.id).exists()

    @patch("collectors.tasks.MinIOClient")
    def test_missing_collection_is_handled_without_raising(self, _mock_minio_cls):
        execute_collection_task(999999)


class TestCalculateStatisticsBranches:
    def test_github_ignores_invalid_dates(self):
        stats = calculate_statistics(
            {
                "pull_requests": [
                    {
                        "details": {"created_at": "not-a-date"},
                        "commits": [],
                        "comments": [],
                        "reviews": [],
                        "review_comments": [],
                    }
                ]
            },
            "github",
        )

        assert "start_date" not in stats
        assert stats["total_items"] == 1

    def test_gitlab_extracts_date_range_and_discussion_counts(self):
        stats = calculate_statistics(
            {
                "merge_requests": [
                    {
                        "details": {"created_at": "2024-02-01T00:00:00Z"},
                        "commits": [{"id": "a"}],
                        "notes": [{"id": 1}],
                        "discussions": [{"id": "d"}],
                    },
                    {
                        "details": {"created_at": "2024-02-03T00:00:00Z"},
                        "commits": [],
                        "notes": [],
                        "discussions": [],
                    },
                ]
            },
            "gitlab",
        )

        assert stats["merge_requests_count"] == 2
        assert stats["discussions_count"] == 1
        assert stats["start_date"] == "01/02/2024"
        assert stats["end_date"] == "03/02/2024"
