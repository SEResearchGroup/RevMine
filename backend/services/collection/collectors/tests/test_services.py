"""Unit tests for the service layer.

Tests cover:
- :class:`~collectors.services.MetricsService`
- :class:`~collectors.services.BranchService`
- :class:`~collectors.services.CollectionService`  (lifecycle operations)
- :class:`~collectors.services.CollectedDataService`
- :class:`~collectors.services.CleanedDataService`
- :func:`~collectors.services.resolve_workspace_token`
- :func:`~collectors.tasks.calculate_statistics`
"""
import pytest
from unittest.mock import MagicMock, patch, call
from datetime import date

from collectors.models import Collection, CleanedData
from collectors.services import (
    MetricsService,
    BranchService,
    CollectionService,
    CollectedDataService,
    DataCleaningService,
    CleanedDataService,
    resolve_workspace_token,
    CollectionServiceError,
    CollectionStateError,
    CollectionValidationError,
    StorageError,
)
from collectors.tasks import calculate_statistics


# =============================================================================
# calculate_statistics (tasks.py helper — pure function)
# =============================================================================

class TestCalculateStatistics:
    def test_github_counts_prs(self):
        data = {"pull_requests": [{"commits": [1, 2], "comments": [], "reviews": [], "review_comments": []}]}
        stats = calculate_statistics(data, "github")
        assert stats["total_items"] == 1
        assert stats["pull_requests_count"] == 1
        assert stats["commits_count"] == 2

    def test_gitlab_counts_mrs(self):
        data = {"merge_requests": [{"commits": [1], "notes": [1, 2], "discussions": []}]}
        stats = calculate_statistics(data, "gitlab")
        assert stats["total_items"] == 1
        assert stats["merge_requests_count"] == 1
        assert stats["commits_count"] == 1
        assert stats["notes_count"] == 2

    def test_empty_github(self):
        stats = calculate_statistics({"pull_requests": []}, "github")
        assert stats["total_items"] == 0

    def test_date_range_extracted(self):
        data = {
            "pull_requests": [
                {
                    "commits": [], "comments": [], "reviews": [], "review_comments": [],
                    "details": {"created_at": "2024-03-15T10:00:00Z"},
                }
            ]
        }
        stats = calculate_statistics(data, "github")
        assert "start_date" in stats
        assert "end_date" in stats


# =============================================================================
# MetricsService
# =============================================================================

@pytest.mark.django_db
class TestMetricsService:
    def test_get_available_metrics_github(self):
        metrics = MetricsService.get_available_metrics("github")
        # Returns a dict keyed by category
        assert isinstance(metrics, dict)
        assert len(metrics) > 0

    def test_get_available_metrics_gitlab(self):
        metrics = MetricsService.get_available_metrics("gitlab")
        assert isinstance(metrics, dict)

    def test_get_metrics_with_collection_status_no_collection(self, create_collection):
        result = MetricsService.get_metrics_with_collection_status(
            user_id=99, repository_id=99, platform="github"
        )
        assert result["has_active_collection"] is False
        assert result["active_collection"] is None

    def test_get_metrics_with_collection_status_has_active(self, create_collection):
        create_collection(status="in_progress", repository_id=10)
        result = MetricsService.get_metrics_with_collection_status(
            user_id=1, repository_id=10, platform="github"
        )
        assert result["has_active_collection"] is True


# =============================================================================
# BranchService
# =============================================================================

class TestBranchService:
    @patch("collectors.infrastructure.providers.branch_fetcher.BranchFetcher.fetch_branches")
    def test_fetch_branches_delegates_to_fetcher(self, mock_fetch):
        mock_fetch.return_value = [{"name": "main"}]
        result = BranchService.fetch_branches("github", "tok", "o/r")
        assert result == [{"name": "main"}]

    @patch("collectors.infrastructure.providers.branch_fetcher.BranchFetcher.fetch_branches")
    def test_fetch_branches_wraps_exception(self, mock_fetch):
        mock_fetch.side_effect = Exception("API error")
        with pytest.raises(CollectionServiceError):
            BranchService.fetch_branches("github", "tok", "o/r")


# =============================================================================
# CollectionService — lifecycle
# =============================================================================

@pytest.mark.django_db
class TestCollectionService:
    def test_get_or_create_creates_new_when_none_active(self, create_collection):
        validated = {
            "repository_id": 50,
            "workspace_id": 1,
            "repository_name": "repo",
            "repository_full_name": "o/repo",
            "platform": "github",
            "token": "tok",
        }
        collection, is_existing = CollectionService.get_or_create_collection(
            user_id=1, validated_data=validated
        )
        assert is_existing is False
        assert collection.status == "pending"

    def test_get_or_create_returns_existing_for_active(self, create_collection):
        existing = create_collection(status="in_progress", repository_id=51)
        validated = {
            "repository_id": 51,
            "workspace_id": 1,
            "repository_name": "repo",
            "repository_full_name": "o/repo",
            "platform": "github",
            "token": "tok",
        }
        collection, is_existing = CollectionService.get_or_create_collection(
            user_id=1, validated_data=validated
        )
        assert is_existing is True
        assert collection.id == existing.id

    def test_configure_metrics_updates_collection(self, create_collection):
        collection = create_collection(status="pending")
        result = CollectionService.configure_metrics(
            collection=collection,
            selected_metrics=["pr_title", "commit_sha"],
            filters={"start_date": date(2024, 1, 1), "end_date": None, "status": []},
        )
        assert result.selected_metrics == ["pr_title", "commit_sha"]

    def test_configure_metrics_rejects_in_progress(self, create_collection):
        collection = create_collection(status="in_progress")
        with pytest.raises(CollectionStateError):
            CollectionService.configure_metrics(
                collection=collection,
                selected_metrics=["pr_title"],
                filters={},
            )

    def test_configure_metrics_persists_for_qualitative_flag(self, create_collection):
        collection = create_collection(status="pending")
        result = CollectionService.configure_metrics(
            collection=collection,
            selected_metrics=["pr_title"],
            filters={"for_qualitative": True},
        )
        assert result.for_qualitative is True

    def test_configure_metrics_defaults_for_qualitative_false(self, create_collection):
        collection = create_collection(status="pending")
        result = CollectionService.configure_metrics(
            collection=collection,
            selected_metrics=["pr_title"],
            filters={},
        )
        assert result.for_qualitative is False

    def test_get_collection_summary(self, create_collection):
        collection = create_collection(
            status="pending",
            selected_metrics=["pr_title", "commit_sha"],
        )
        summary = CollectionService.get_collection_summary(collection)
        assert summary["metrics_count"] == 2
        assert "repository" in summary

    @patch("collectors.services.run_collection_in_background")
    def test_execute_collection_starts_background(self, mock_bg, create_collection):
        collection = create_collection(
            status="pending",
            selected_metrics=["pr_title"],
        )
        CollectionService.execute_collection(collection)
        mock_bg.assert_called_once_with(collection.id)

    def test_execute_collection_requires_metrics(self, create_collection):
        collection = create_collection(status="pending", selected_metrics=[])
        with pytest.raises(CollectionValidationError):
            CollectionService.execute_collection(collection)

    def test_execute_collection_rejects_completed_status(self, create_collection):
        collection = create_collection(status="completed")
        with pytest.raises(CollectionStateError):
            CollectionService.execute_collection(collection)

    def test_pause_collection(self, create_collection):
        collection = create_collection(status="in_progress")
        with patch("collectors.services.cancellation_registry") as reg:
            reg.cancel = MagicMock()
            result = CollectionService.pause_collection(collection)
        assert result.status == "paused"
        assert result.error_message == "Collection paused by user"

    def test_pause_requires_in_progress(self, create_collection):
        collection = create_collection(status="pending")
        with pytest.raises(CollectionStateError):
            CollectionService.pause_collection(collection)

    def test_get_user_collections(self, create_collection):
        create_collection(status="completed", repository_id=60)
        create_collection(status="pending", repository_id=61)
        result = CollectionService.get_user_collections(1)
        assert result.count() >= 2

    def test_get_repository_history(self, create_collection):
        create_collection(status="completed", repository_id=70)
        create_collection(status="pendingXXX", repository_id=70)  # excluded
        history = CollectionService.get_repository_history(user_id=1, repository_id=70)
        for c in history:
            assert c.status != "pending"

    @patch("collectors.services.MinIOClient")
    def test_delete_collection_deletes_minio_files(self, mock_minio_cls, create_collection):
        mock_minio = MagicMock()
        mock_minio_cls.return_value = mock_minio
        collection = create_collection(
            status="completed",
            raw_data_filename="data.json",
        )
        CollectionService.delete_collection(collection)
        mock_minio.delete_file.assert_called_with("data.json")

    @patch("collectors.services.MinIOClient")
    def test_delete_collection_raises_storage_error_on_exception(
        self, mock_minio_cls, create_collection
    ):
        mock_minio = MagicMock()
        mock_minio.delete_file.side_effect = Exception("oops")
        mock_minio_cls.return_value = mock_minio
        collection = create_collection(status="completed", raw_data_filename="x.json")
        with pytest.raises(StorageError):
            CollectionService.delete_collection(collection)


# =============================================================================
# CollectedDataService
# =============================================================================

@pytest.mark.django_db
class TestCollectedDataService:
    @patch("collectors.services.MinIOClient")
    def test_get_collected_data_found(self, mock_minio_cls, create_collection):
        payload = {"pull_requests": [{"id": 1}]}
        mock_minio = MagicMock()
        mock_minio.get_json.return_value = payload
        mock_minio_cls.return_value = mock_minio

        collection = create_collection(status="completed", raw_data_filename="data.json")
        result = CollectedDataService.get_collected_data(collection)
        assert result["found"] is True
        assert result["raw_data"] == payload

    @patch("collectors.services.MinIOClient")
    def test_get_collected_data_no_filename(self, mock_minio_cls, create_collection):
        collection = create_collection(status="completed")
        result = CollectedDataService.get_collected_data(collection)
        assert result["found"] is False

    @patch("collectors.services.MinIOClient")
    def test_get_collected_data_minio_returns_none(self, mock_minio_cls, create_collection):
        mock_minio = MagicMock()
        mock_minio.get_json.return_value = None
        mock_minio_cls.return_value = mock_minio
        collection = create_collection(status="completed", raw_data_filename="missing.json")
        result = CollectedDataService.get_collected_data(collection)
        assert result["found"] is False


# =============================================================================
# resolve_workspace_token
# =============================================================================

class TestResolveWorkspaceToken:
    @patch("collectors.services._get_rr_client")
    def test_returns_token_on_success(self, mock_get_rr):
        mock_client = MagicMock()
        mock_client.call.return_value = {"status": "ok", "token": "abc123"}
        mock_get_rr.return_value = mock_client

        token = resolve_workspace_token(user_id=1, workspace_id=2, platform="github")
        assert token == "abc123"

    @patch("collectors.services._get_rr_client")
    def test_raises_on_bad_response(self, mock_get_rr):
        mock_client = MagicMock()
        mock_client.call.return_value = {"status": "error"}
        mock_get_rr.return_value = mock_client

        with pytest.raises(CollectionValidationError):
            resolve_workspace_token(user_id=1, workspace_id=2, platform="github")

    @patch("collectors.services._get_rr_client")
    def test_raises_when_token_missing(self, mock_get_rr):
        mock_client = MagicMock()
        mock_client.call.return_value = {"status": "ok", "token": None}
        mock_get_rr.return_value = mock_client

        with pytest.raises(CollectionValidationError):
            resolve_workspace_token(user_id=1, workspace_id=2, platform="github")
