"""Integration tests — full pipeline (collect → clean → export).

These tests simulate the end-to-end flow without real network calls:

    API request → Service orchestration → (mocked) Provider → Processor → Exporter → MinIO

We verify that:
- A collection can be created, configured, and executed end-to-end.
- The statistics calculation matches the collected data.
- Data cleaning correctly filters items and produces valid CSV.
- The CleanedData record is marked as completed.
"""
import io
import json
import pytest
from datetime import date
from unittest.mock import patch, MagicMock

from django.utils import timezone

from collectors.models import Collection, CleanedData
from collectors.services import (
    CollectionService,
    CollectedDataService,
    CleanedDataService,
    DataCleaningService,
    CollectionStateError,
)
from collectors.tasks import calculate_statistics


# ---------------------------------------------------------------------------
# Sample fixtures
# ---------------------------------------------------------------------------

_GITHUB_DATA = {
    "project_created_at": "2020-01-01T00:00:00Z",
    "pull_requests": [
        {
            "pull_request_number": 1,
            "details": {
                "number": 1,
                "title": "Add feature",
                "state": "closed",
                "merged": True,
                "user": {"login": "alice"},
                "created_at": "2024-03-01T10:00:00Z",
                "merged_at": "2024-03-02T10:00:00Z",
                "closed_at": "2024-03-02T10:00:00Z",
                "additions": 10,
                "deletions": 2,
            },
            "commits": [{"commit_sha": "abc"}],
            "comments": [],
            "reviews": [],
            "review_comments": [],
            "files": [{"filename": "module.py", "additions": 10, "deletions": 2}],
        },
        {
            "pull_request_number": 2,
            "details": {
                "number": 2,
                "title": "Fix bug",
                "state": "open",
                "merged": False,
                "user": {"login": "bob"},
                "created_at": "2024-06-01T10:00:00Z",
                "merged_at": None,
                "closed_at": None,
                "additions": 5,
                "deletions": 1,
            },
            "commits": [],
            "comments": [{"user": {"login": "alice"}, "created_at": "2024-06-02T10:00:00Z", "body": "LGTM"}],
            "reviews": [],
            "review_comments": [],
            "files": [{"filename": "readme.md", "additions": 5, "deletions": 1}],
        },
    ],
}


# ---------------------------------------------------------------------------
# Pipeline: create → configure → execute
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestCollectionPipeline:
    """Walk the lifecycle of a collection through all service methods."""

    def test_full_lifecycle(self, create_collection):
        # 1. Create collection
        validated = {
            "repository_id": 200,
            "workspace_id": 1,
            "repository_name": "pipeline-repo",
            "repository_full_name": "org/pipeline-repo",
            "platform": "github",
            "token": "tok",
        }
        collection, is_existing = CollectionService.get_or_create_collection(
            user_id=1, validated_data=validated
        )
        assert is_existing is False
        assert collection.status == "pending"

        # 2. Configure metrics
        collection = CollectionService.configure_metrics(
            collection=collection,
            selected_metrics=["pr_title", "commit_sha"],
            filters={
                "start_date": date(2024, 1, 1),
                "end_date": date(2024, 12, 31),
                "status": [],
            },
        )
        assert collection.selected_metrics == ["pr_title", "commit_sha"]
        assert collection.filters["start_date"] == "2024-01-01"

        # 3. Validate summary
        summary = CollectionService.get_collection_summary(collection)
        assert summary["metrics_count"] == 2
        assert summary["repository"] == "org/pipeline-repo"

        # 4. Execute (mock bg thread)
        with patch("collectors.services.run_collection_in_background") as mock_bg:
            collection = CollectionService.execute_collection(collection)
            mock_bg.assert_called_once_with(collection.id)

    def test_configure_rejected_for_completed_collection(self, create_collection):
        collection = create_collection(status="completed")
        with pytest.raises(CollectionStateError):
            CollectionService.configure_metrics(
                collection=collection,
                selected_metrics=["pr_title"],
                filters={},
            )

    def test_collection_can_be_paused_then_resumed(self, create_collection):
        collection = create_collection(
            status="in_progress",
            selected_metrics=["pr_title"],
            last_collected_item_id="5",
        )
        with patch("collectors.services.cancellation_registry"):
            collection = CollectionService.pause_collection(collection)
        assert collection.status == "paused"
        assert collection.can_resume is True

        with patch("collectors.services.run_collection_in_background") as mock_bg:
            CollectionService.resume_collection(collection)
            mock_bg.assert_called_once_with(collection.id, resume=True)


# ---------------------------------------------------------------------------
# Statistics calculation
# ---------------------------------------------------------------------------

class TestStatisticsCalculation:
    def test_stats_match_github_data(self):
        stats = calculate_statistics(_GITHUB_DATA, "github")
        assert stats["total_items"] == 2
        assert stats["pull_requests_count"] == 2
        assert stats["commits_count"] == 1   # only pr #1 has commits
        assert stats["comments_count"] == 1  # pr #2 has 1 comment

    def test_gitlab_stats(self):
        data = {
            "merge_requests": [
                {
                    "details": {"created_at": "2024-05-01T00:00:00Z"},
                    "commits": [1, 2],
                    "notes": [1],
                    "discussions": [],
                }
            ]
        }
        stats = calculate_statistics(data, "gitlab")
        assert stats["total_items"] == 1
        assert stats["commits_count"] == 2
        assert stats["notes_count"] == 1


# ---------------------------------------------------------------------------
# Data cleaning pipeline
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestDataCleaningPipeline:
    @patch("collectors.services.MinIOClient")
    def test_create_cleaned_data_produces_csv(self, mock_minio_cls, create_collection):
        """End-to-end: CleanedData is created and both CSV files are saved to MinIO."""
        storage = {}
        mock_minio = MagicMock()
        mock_minio.get_json.return_value = _GITHUB_DATA
        mock_minio.generate_filename.side_effect = lambda repo, cid, ext: f"{repo}_{cid}.{ext}"
        mock_minio.save_csv.side_effect = lambda content, fname: storage.update({fname: content}) or True
        mock_minio_cls.return_value = mock_minio

        collection = create_collection(
            status="completed",
            platform="github",
            raw_data_filename="data.json",
        )
        cleaned = CleanedDataService.create_cleaned_data(
            collection=collection,
            start_date=None,
            end_date=None,
            filters={},
            selected_features=[],
        )

        assert cleaned.status == "completed"
        assert cleaned.structured_csv_filename is not None
        assert cleaned.statistics_csv_filename is not None
        # Verify both CSVs were "saved" to our storage stub
        assert mock_minio.save_csv.call_count == 2

    @patch("collectors.services.MinIOClient")
    def test_create_cleaned_data_with_date_filter(self, mock_minio_cls, create_collection):
        """Only items within the date range should be included."""
        mock_minio = MagicMock()
        mock_minio.get_json.return_value = _GITHUB_DATA
        mock_minio.generate_filename.side_effect = lambda r, c, e: f"{r}_{c}.{e}"
        mock_minio.save_csv.return_value = True
        mock_minio_cls.return_value = mock_minio

        collection = create_collection(
            status="completed",
            platform="github",
            raw_data_filename="data.json",
        )
        # Filter to only include March 2024 (PR #1)
        cleaned = CleanedDataService.create_cleaned_data(
            collection=collection,
            start_date=date(2024, 3, 1),
            end_date=date(2024, 3, 31),
            filters={},
        )
        assert cleaned.status == "completed"
        stats = cleaned.stats
        # Should have 1 PR after date filter
        assert stats.get("pull_requests_count", 0) == 1

    @patch("collectors.services.MinIOClient")
    def test_create_cleaned_data_fails_gracefully(self, mock_minio_cls, create_collection):
        """On MinIO failure, CleanedData should be marked as failed."""
        mock_minio = MagicMock()
        mock_minio.get_json.side_effect = Exception("MinIO down")
        mock_minio_cls.return_value = mock_minio

        collection = create_collection(
            status="completed",
            platform="github",
            raw_data_filename="data.json",
        )
        with pytest.raises(Exception):
            CleanedDataService.create_cleaned_data(collection=collection)

        # Verify the CleanedData row was marked as failed
        cd = CleanedData.objects.filter(collection=collection).first()
        assert cd is not None
        assert cd.status == "failed"
        assert cd.error_message is not None

    @patch("collectors.services.MinIOClient")
    def test_collection_must_be_completed_for_cleaning(self, mock_minio_cls, create_collection):
        mock_minio_cls.return_value = MagicMock()
        collection = create_collection(status="in_progress")
        with pytest.raises(CollectionStateError):
            CleanedDataService.create_cleaned_data(collection=collection)
