"""API layer tests — DRF views, serializers, URL routing.

Tests cover:
- HTTP status codes and response shape for every endpoint
- Serializer validation (required fields, date ordering)
- Authentication enforcement (X-User-ID header)
"""
import pytest
from unittest.mock import patch, MagicMock
from rest_framework import status
from rest_framework.test import APIClient
from django.core.files.uploadedfile import SimpleUploadedFile

from collectors.models import Collection
from collectors.services import (
    CollectionServiceError,
    CollectionStateError,
    CollectionValidationError,
    StorageError,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

USER_ID = "1"


def _auth_client():
    client = APIClient()
    client.credentials(HTTP_X_USER_ID=USER_ID)
    return client


# ---------------------------------------------------------------------------
# Authentication guard
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAuthGuard:
    def test_unauthenticated_start_collection_returns_401(self):
        resp = APIClient().post("/api/collections/start/", {}, format="json")
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_unauthenticated_metrics_returns_401(self):
        resp = APIClient().get("/api/collections/metrics/?platform=github&repository_id=1")
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_invalid_user_id_returns_401(self):
        client = APIClient()
        client.credentials(HTTP_X_USER_ID="not-an-int")
        resp = client.get("/api/collections/metrics/?platform=github&repository_id=1")
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# StartCollection
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestStartCollectionView:
    def test_missing_required_fields_returns_400(self):
        resp = _auth_client().post(
            "/api/collections/start/",
            {"platform": "github"},  # missing repository_id etc.
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    @patch("collectors.services.CollectionService.get_or_create_collection")
    @patch("collectors.services.MetricsService.get_available_metrics", return_value=[])
    def test_creates_new_collection_returns_201(self, _metrics, mock_create, create_collection):
        fake_collection = create_collection()
        mock_create.return_value = (fake_collection, False)

        resp = _auth_client().post(
            "/api/collections/start/",
            {
                "repository_id": 1,
                "workspace_id": 1,
                "repository_name": "repo",
                "repository_full_name": "owner/repo",
                "platform": "github",
                "token": "tok",
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["success"] is True
        assert resp.data["is_existing"] is False

    @patch(
        "collectors.api.views.resolve_repository_metadata",
        return_value={
            "workspace_id": 4,
            "repository_id": 9,
            "repository_name": "repo",
            "repository_full_name": "owner/repo",
            "platform": "github",
            "repository_url": "https://github.com/owner/repo",
            "default_branch": "main",
            "external_id": "123",
        },
    )
    @patch("collectors.services.CollectionService.get_or_create_collection")
    @patch("collectors.services.MetricsService.get_available_metrics", return_value=[])
    def test_start_resolves_repository_metadata_from_ids(
        self, _metrics, mock_create, mock_repository, create_collection
    ):
        fake_collection = create_collection()
        mock_create.return_value = (fake_collection, False)

        resp = _auth_client().post(
            "/api/collections/start/",
            {"workspace_id": 4, "repository_id": 9},
            format="json",
        )

        assert resp.status_code == status.HTTP_201_CREATED
        mock_repository.assert_called_once_with(user_id=1, workspace_id=4, repository_id=9)
        validated = mock_create.call_args.kwargs["validated_data"]
        assert validated["platform"] == "github"
        assert validated["repository_full_name"] == "owner/repo"

    @patch("collectors.services.CollectionService.get_or_create_collection")
    @patch("collectors.services.MetricsService.get_available_metrics", return_value=[])
    def test_existing_collection_returns_200(self, _metrics, mock_create, create_collection):
        fake_collection = create_collection(status="in_progress")
        mock_create.return_value = (fake_collection, True)

        resp = _auth_client().post(
            "/api/collections/start/",
            {
                "repository_id": 1,
                "workspace_id": 1,
                "repository_name": "repo",
                "repository_full_name": "owner/repo",
                "platform": "github",
                "token": "tok",
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["is_existing"] is True


# ---------------------------------------------------------------------------
# Automation preview
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAutomationPreviewView:
    @patch(
        "collectors.automation.resolve_repository_metadata",
        return_value={
            "workspace_id": 4,
            "repository_id": 9,
            "repository_name": "repo",
            "repository_full_name": "owner/repo",
            "platform": "github",
            "repository_url": "https://github.com/owner/repo",
            "default_branch": "main",
            "external_id": "123",
        },
    )
    @patch("collectors.automation.requests.post")
    def test_generates_collection_draft(self, mock_post, mock_repository):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "model": "openai/gpt-4o-mini",
            "result": {
                "intent": "collect",
                "branch": ["main"],
                "metrics": ["creation_date", "commit_messages"],
                "basic_filters": {
                    "date_range": {
                        "start_date": "2026-01-01",
                        "end_date": "2026-02-01",
                    },
                    "pr_status": ["merged"],
                },
                "cleaning_filters": {
                    "refined_date_range": None,
                    "file_extensions": ["py"],
                    "authors": ["alice"],
                    "keywords": {
                        "fields": ["title"],
                        "terms": ["bug"],
                    },
                },
                "features": ["lead_time"],
            },
        }

        resp = _auth_client().post(
            "/api/collections/automation/preview/",
            {
                "workspace_id": 4,
                "repository_id": 9,
                "prompt": "Collect merged bug PRs on main",
                "llm_provider": "openrouter",
                "model": "openai/gpt-4o-mini",
            },
            format="json",
        )

        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["success"] is True
        draft = resp.data["draft"]
        assert draft["collection"]["branch_name"] == "main"
        assert draft["collection"]["status"] == ["merged"]
        assert "pr_creation_date" in draft["collection"]["selected_metrics"]
        assert "commit_message" in draft["collection"]["selected_metrics"]
        assert "pr_merge_date" in draft["collection"]["selected_metrics"]
        assert draft["cleaning"]["filters"]["file_extensions"] == [".py"]
        assert draft["cleaning"]["filters"]["authors"] == ["alice"]
        assert draft["cleaning"]["filters"]["keyword_filters"] == [
            {"field": "title", "keywords": ["bug"]}
        ]
        assert draft["cleaning"]["selected_features"] == ["Lead_Time"]
        mock_repository.assert_called_once_with(user_id=1, workspace_id=4, repository_id=9)
        assert mock_post.call_args.kwargs["json"]["model"] == "openai/gpt-4o-mini"

    def test_requires_prompt(self):
        resp = _auth_client().post(
            "/api/collections/automation/preview/",
            {"workspace_id": 4, "repository_id": 9, "prompt": ""},
            format="json",
        )

        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.data["error"] == "prompt is required"

    @patch(
        "collectors.automation.resolve_repository_metadata",
        return_value={
            "workspace_id": 4,
            "repository_id": 9,
            "repository_name": "repo",
            "repository_full_name": "owner/repo",
            "platform": "github",
            "default_branch": "main",
        },
    )
    @patch("collectors.automation.requests.post")
    def test_llm_error_returns_502(self, mock_post, _mock_repository):
        mock_post.return_value.status_code = 502
        mock_post.return_value.json.return_value = {"detail": "model unavailable"}

        resp = _auth_client().post(
            "/api/collections/automation/preview/",
            {"workspace_id": 4, "repository_id": 9, "prompt": "Collect PRs"},
            format="json",
        )

        assert resp.status_code == status.HTTP_502_BAD_GATEWAY
        assert "model unavailable" in resp.data["error"]


# ---------------------------------------------------------------------------
# GetAvailableMetrics
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestGetAvailableMetricsView:
    def test_missing_repository_id_returns_400(self):
        resp = _auth_client().get("/api/collections/metrics/?platform=github")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    @patch("collectors.services.MetricsService.get_metrics_with_collection_status")
    def test_returns_200_with_metrics(self, mock_svc):
        mock_svc.return_value = {
            "available_metrics": [{"value": "pr_title", "label": "PR Title"}],
            "platform": "github",
            "has_active_collection": False,
            "active_collection": None,
        }
        resp = _auth_client().get(
            "/api/collections/metrics/?platform=github&repository_id=1"
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["success"] is True


# ---------------------------------------------------------------------------
# Branch discovery
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestBranchesViews:
    def test_repository_branches_requires_platform_and_repository(self):
        resp = _auth_client().post("/api/collections/branches/", {"platform": "github"}, format="json")

        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "repository_full_name" in resp.data["error"]

    def test_repository_branches_requires_workspace_when_token_missing(self):
        resp = _auth_client().post(
            "/api/collections/branches/",
            {"platform": "github", "repository_full_name": "owner/repo"},
            format="json",
        )

        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    @patch("collectors.api.views.BranchService.fetch_date_range", return_value={"first_date": "2024-01-01"})
    @patch("collectors.api.views.BranchService.fetch_branches", return_value=[{"name": "main"}])
    def test_repository_branches_returns_branches_and_date_range(self, mock_fetch, mock_range):
        resp = _auth_client().post(
            "/api/collections/branches/",
            {
                "platform": "github",
                "token": "token",
                "repository_full_name": "owner/repo",
                "default_branch": "main",
            },
            format="json",
        )

        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["branches"] == [{"name": "main"}]
        assert resp.data["date_range"] == {"first_date": "2024-01-01"}
        mock_fetch.assert_called_once()
        mock_range.assert_called_once()

    @patch("collectors.api.views.resolve_workspace_token", return_value="resolved-token")
    @patch("collectors.api.views.BranchService.fetch_date_range", return_value={})
    @patch("collectors.api.views.BranchService.fetch_branches", return_value=[])
    def test_repository_branches_resolves_workspace_token(self, mock_fetch, _range, mock_token):
        resp = _auth_client().post(
            "/api/collections/branches/",
            {"platform": "gitlab", "workspace_id": 4, "repository_full_name": "group/repo"},
            format="json",
        )

        assert resp.status_code == status.HTTP_200_OK
        mock_token.assert_called_once_with(user_id=1, workspace_id=4, platform="gitlab")
        assert mock_fetch.call_args.kwargs["token"] == "resolved-token"

    @patch(
        "collectors.api.views.resolve_repository_metadata",
        return_value={
            "workspace_id": 4,
            "repository_id": 9,
            "repository_name": "repo",
            "repository_full_name": "owner/repo",
            "platform": "github",
            "default_branch": "main",
        },
    )
    @patch("collectors.api.views.resolve_workspace_token", return_value="resolved-token")
    @patch("collectors.api.views.BranchService.fetch_date_range", return_value={})
    @patch("collectors.api.views.BranchService.fetch_branches", return_value=[{"name": "main"}])
    def test_repository_branches_resolves_metadata_from_ids(
        self, mock_fetch, _range, mock_token, mock_repository
    ):
        resp = _auth_client().post(
            "/api/collections/branches/",
            {"workspace_id": 4, "repository_id": 9},
            format="json",
        )

        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["branches"] == [{"name": "main"}]
        assert resp.data["default_branch"] == "main"
        mock_repository.assert_called_once_with(user_id=1, workspace_id=4, repository_id=9)
        mock_token.assert_called_once_with(user_id=1, workspace_id=4, platform="github")
        assert mock_fetch.call_args.kwargs["repo_full_name"] == "owner/repo"

    @patch("collectors.api.views.BranchService.fetch_branches", side_effect=CollectionServiceError("boom"))
    def test_repository_branches_wraps_service_error(self, _mock_fetch):
        resp = _auth_client().post(
            "/api/collections/branches/",
            {"platform": "github", "token": "token", "repository_full_name": "owner/repo"},
            format="json",
        )

        assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert resp.data["branches"] == []

    @patch("collectors.api.views.BranchService.fetch_branches_for_collection", return_value=[{"name": "main"}])
    def test_collection_branches_returns_default_branch(self, mock_fetch, create_collection):
        collection = create_collection(default_branch="develop")
        resp = _auth_client().get(f"/api/collections/plans/{collection.id}/branches/")

        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["default_branch"] == "develop"
        mock_fetch.assert_called_once_with(collection)


# ---------------------------------------------------------------------------
# CollectionStatus
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestCollectionStatusView:
    def test_nonexistent_plan_returns_404(self):
        resp = _auth_client().get("/api/collections/plans/99999/status/")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_existing_plan_returns_200(self, create_collection):
        collection = create_collection(status="in_progress")
        resp = _auth_client().get(f"/api/collections/plans/{collection.id}/status/")
        assert resp.status_code == status.HTTP_200_OK
        assert "status" in resp.data


# ---------------------------------------------------------------------------
# ConfigureMetrics
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestConfigureMetricsView:
    def test_invalid_serializer_returns_400(self, create_collection):
        collection = create_collection(status="pending")
        resp = _auth_client().post(
            f"/api/collections/plans/{collection.id}/configure/",
            {},  # missing selected_metrics
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_end_before_start_date_returns_400(self, create_collection):
        collection = create_collection(status="pending")
        resp = _auth_client().post(
            f"/api/collections/plans/{collection.id}/configure/",
            {
                "selected_metrics": ["pr_title"],
                "start_date": "2024-12-31",
                "end_date": "2024-01-01",
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_valid_config_returns_200(self, create_collection):
        collection = create_collection(status="pending")
        resp = _auth_client().post(
            f"/api/collections/plans/{collection.id}/configure/",
            {
                "selected_metrics": ["pr_title", "commit_sha"],
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
                "status": ["open", "closed"],
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["success"] is True


# ---------------------------------------------------------------------------
# ExecuteCollection
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestExecuteCollectionView:
    @patch("collectors.services.CollectionService.execute_collection")
    def test_returns_200_and_delegates_to_service(self, mock_exec, create_collection):
        collection = create_collection(status="pending", selected_metrics=["pr_title"])
        mock_exec.return_value = collection

        resp = _auth_client().post(
            f"/api/collections/plans/{collection.id}/execute/"
        )
        assert resp.status_code == status.HTTP_200_OK
        mock_exec.assert_called_once()

    def test_missing_metrics_returns_400(self, create_collection):
        collection = create_collection(status="pending", selected_metrics=[])
        resp = _auth_client().post(
            f"/api/collections/plans/{collection.id}/execute/"
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


# ---------------------------------------------------------------------------
# Validate / Resume / History
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestLifecycleReadViews:
    @patch("collectors.api.views.CollectionService.get_collection_summary", return_value={"metrics_count": 2})
    def test_validate_collection_returns_summary(self, mock_summary, create_collection):
        collection = create_collection(status="pending")

        resp = _auth_client().get(f"/api/collections/plans/{collection.id}/validate/")

        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["summary"] == {"metrics_count": 2}
        mock_summary.assert_called_once_with(collection)

    @patch("collectors.api.views.CollectionService.resume_collection")
    def test_resume_collection_returns_last_collected_item(self, mock_resume, create_collection):
        collection = create_collection(status="paused", last_collected_item_id="42")
        mock_resume.return_value = collection

        resp = _auth_client().post(f"/api/collections/plans/{collection.id}/resume/")

        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["last_collected_item"] == "42"

    @patch("collectors.api.views.CollectionService.resume_collection", side_effect=CollectionStateError("not resumable"))
    def test_resume_collection_state_error_returns_400(self, _mock_resume, create_collection):
        collection = create_collection(status="completed")

        resp = _auth_client().post(f"/api/collections/plans/{collection.id}/resume/")

        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_repository_history_excludes_pending_collections(self, create_collection):
        create_collection(status="completed", repository_id=90)
        create_collection(status="failed", repository_id=90)

        resp = _auth_client().get("/api/collections/history/90/")

        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["success"] is True
        assert resp.data["total"] >= 2


# ---------------------------------------------------------------------------
# PauseCollection
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestPauseCollectionView:
    def test_pause_not_in_progress_returns_400(self, create_collection):
        collection = create_collection(status="pending")
        resp = _auth_client().post(f"/api/collections/plans/{collection.id}/pause/")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_pause_in_progress_returns_200(self, create_collection):
        collection = create_collection(status="in_progress")
        with patch("collectors.services.cancellation_registry"):
            resp = _auth_client().post(
                f"/api/collections/plans/{collection.id}/pause/"
            )
        assert resp.status_code == status.HTTP_200_OK


# ---------------------------------------------------------------------------
# DeleteCollection
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestDeleteCollectionView:
    @patch("collectors.services.CollectionService.delete_collection")
    def test_delete_returns_200(self, mock_del, create_collection):
        collection = create_collection(status="completed")
        resp = _auth_client().delete(
            f"/api/collections/collections/{collection.id}/delete/"
        )
        assert resp.status_code == status.HTTP_200_OK
        mock_del.assert_called_once()

    def test_delete_not_found_returns_404(self):
        resp = _auth_client().delete("/api/collections/collections/99999/delete/")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    @patch("collectors.api.views.CollectionService.delete_collection", side_effect=StorageError("minio down"))
    def test_delete_storage_error_returns_500(self, _mock_del, create_collection):
        collection = create_collection(status="completed")

        resp = _auth_client().delete(
            f"/api/collections/collections/{collection.id}/delete/"
        )

        assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


# ---------------------------------------------------------------------------
# CollectionPlans list
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestCollectionPlanListView:
    def test_returns_user_collections(self, create_collection):
        create_collection(status="completed")
        create_collection(status="pending", repository_id=2)
        resp = _auth_client().get("/api/collections/plans/")
        assert resp.status_code == status.HTTP_200_OK
        assert isinstance(resp.data, list)
        assert len(resp.data) >= 2


# ---------------------------------------------------------------------------
# Raw collected data and download
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestCollectedDataViews:
    @patch("collectors.api.views.CollectedDataService.get_collected_data", return_value={"found": False})
    def test_collected_data_not_found_returns_404(self, _mock_service, create_collection):
        collection = create_collection(status="completed")

        resp = _auth_client().get(f"/api/collections/plans/{collection.id}/data/")

        assert resp.status_code == status.HTTP_404_NOT_FOUND

    @patch("collectors.api.views.CollectedDataService.get_collected_data", side_effect=StorageError("offline"))
    def test_collected_data_storage_error_returns_500(self, _mock_service, create_collection):
        collection = create_collection(status="completed")

        resp = _auth_client().get(f"/api/collections/plans/{collection.id}/data/")

        assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert resp.data["error"] == "Failed to retrieve collected data"

    @patch("collectors.api.views.CollectedDataService.get_raw_json", return_value={"pull_requests": []})
    def test_download_collection_json_success(self, _mock_service, create_collection):
        collection = create_collection(status="completed", raw_data_filename="raw.json")

        resp = _auth_client().get(f"/api/collections/collections/{collection.id}/download/")

        assert resp.status_code == status.HTTP_200_OK
        assert resp["Content-Type"] == "application/json"
        assert "raw.json" in resp["Content-Disposition"]

    def test_download_collection_json_requires_filename(self, create_collection):
        collection = create_collection(status="completed", raw_data_filename="")

        resp = _auth_client().get(f"/api/collections/collections/{collection.id}/download/")

        assert resp.status_code == status.HTTP_404_NOT_FOUND

    @patch("collectors.api.views.CollectedDataService.get_raw_json", return_value=None)
    def test_download_collection_json_missing_storage_file(self, _mock_service, create_collection):
        collection = create_collection(status="completed", raw_data_filename="raw.json")

        resp = _auth_client().get(f"/api/collections/collections/{collection.id}/download/")

        assert resp.status_code == status.HTTP_404_NOT_FOUND

    @patch("collectors.api.views.CollectedDataService.get_raw_json", side_effect=StorageError("offline"))
    def test_download_collection_json_storage_unavailable(self, _mock_service, create_collection):
        collection = create_collection(status="completed", raw_data_filename="raw.json")

        resp = _auth_client().get(f"/api/collections/collections/{collection.id}/download/")

        assert resp.status_code == status.HTTP_503_SERVICE_UNAVAILABLE


# ---------------------------------------------------------------------------
# Data cleaning and CSV endpoints
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestDataCleaningViews:
    @patch("collectors.api.views.DataCleaningService.get_cleaning_config", return_value={"available_authors": ["alice"]})
    def test_cleaning_config_success(self, _mock_service, create_collection):
        collection = create_collection(status="completed")

        resp = _auth_client().get(f"/api/collections/plans/{collection.id}/cleaning-config/")

        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["success"] is True
        assert resp.data["available_authors"] == ["alice"]

    @patch("collectors.api.views.DataCleaningService.get_cleaning_config", side_effect=CollectionStateError("not complete"))
    def test_cleaning_config_state_error(self, _mock_service, create_collection):
        collection = create_collection(status="pending")

        resp = _auth_client().get(f"/api/collections/plans/{collection.id}/cleaning-config/")

        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    @patch("collectors.api.views.DataCleaningService.get_cleaning_config", side_effect=StorageError("missing raw"))
    def test_cleaning_config_storage_error(self, _mock_service, create_collection):
        collection = create_collection(status="completed")

        resp = _auth_client().get(f"/api/collections/plans/{collection.id}/cleaning-config/")

        assert resp.status_code == status.HTTP_404_NOT_FOUND

    @patch("collectors.api.views.DataCleaningService.apply_filters_and_create_csv")
    def test_apply_filters_success(self, mock_service, create_collection):
        collection = create_collection(status="completed")
        mock_service.return_value = {
            "structured_csv_filename": "structured.csv",
            "statistics_csv_filename": "stats.csv",
        }

        resp = _auth_client().post(
            f"/api/collections/plans/{collection.id}/apply-filters/",
            {"file_extensions": [".py"], "authors": ["alice"], "replace_json": True},
            format="json",
        )

        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["structured_csv_filename"] == "structured.csv"
        assert mock_service.call_args.kwargs["filters"]["file_extensions"] == [".py"]

    @patch("collectors.api.views.DataCleaningService.apply_filters_and_create_csv", side_effect=StorageError("raw missing"))
    def test_apply_filters_storage_error(self, _mock_service, create_collection):
        collection = create_collection(status="completed")

        resp = _auth_client().post(f"/api/collections/plans/{collection.id}/apply-filters/", {}, format="json")

        assert resp.status_code == status.HTTP_404_NOT_FOUND

    @patch("collectors.api.views.DataCleaningService.apply_filters_and_create_csv", side_effect=RuntimeError("bad csv"))
    def test_apply_filters_unexpected_error(self, _mock_service, create_collection):
        collection = create_collection(status="completed")

        resp = _auth_client().post(f"/api/collections/plans/{collection.id}/apply-filters/", {}, format="json")

        assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


@pytest.mark.django_db
class TestCleanedDataViews:
    def test_collection_cleaned_data_list(self, create_collection, create_cleaned_data):
        collection = create_collection(status="completed")
        create_cleaned_data(collection=collection, structured_csv_filename="structured.csv")

        resp = _auth_client().get(f"/api/collections/collections/{collection.id}/cleaned-data/")

        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["success"] is True
        assert len(resp.data["cleaned_data"]) == 1

    @patch("collectors.api.views.CleanedDataService.create_cleaned_data")
    def test_create_cleaned_data_success(self, mock_service, create_collection, create_cleaned_data):
        collection = create_collection(status="completed")
        cleaned = create_cleaned_data(collection=collection)
        mock_service.return_value = cleaned

        resp = _auth_client().post(
            "/api/collections/cleaned-data/",
            {"collection_id": collection.id, "selected_features": ["pr_title"], "filters": {}},
            format="json",
        )

        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["success"] is True

    @patch("collectors.api.views.CleanedDataService.create_cleaned_data", side_effect=StorageError("minio"))
    def test_create_cleaned_data_storage_error(self, _mock_service, create_collection):
        collection = create_collection(status="completed")

        resp = _auth_client().post(
            "/api/collections/cleaned-data/",
            {"collection_id": collection.id, "selected_features": ["pr_title"], "filters": {}},
            format="json",
        )

        assert resp.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    def test_cleaned_data_detail_permission_denied(self, create_collection, create_cleaned_data):
        other_collection = create_collection(user_id=2, repository_id=222, status="completed")
        cleaned = create_cleaned_data(collection=other_collection)

        resp = _auth_client().get(f"/api/collections/cleaned-data/{cleaned.id}/")

        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_cleaned_data_detail_get_success(self, create_cleaned_data):
        cleaned = create_cleaned_data()

        resp = _auth_client().get(f"/api/collections/cleaned-data/{cleaned.id}/")

        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["id"] == cleaned.id

    @patch("collectors.api.views.CleanedDataService.delete_cleaned_data", side_effect=StorageError("locked"))
    def test_cleaned_data_delete_storage_error(self, _mock_service, create_cleaned_data):
        cleaned = create_cleaned_data()

        resp = _auth_client().delete(f"/api/collections/cleaned-data/{cleaned.id}/")

        assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    @patch("collectors.api.views.CleanedDataService.get_csv_for_download", return_value=b"a,b\n1,2\n")
    def test_download_cleaned_csv_success(self, _mock_service, create_cleaned_data):
        cleaned = create_cleaned_data(structured_csv_filename="structured.csv")

        resp = _auth_client().get(f"/api/collections/cleaned-data/{cleaned.id}/download/structured/")

        assert resp.status_code == status.HTTP_200_OK
        assert resp["Content-Type"] == "text/csv"
        assert b"1,2" in b"".join(resp.streaming_content)

    def test_download_cleaned_csv_invalid_user_id(self, create_cleaned_data):
        cleaned = create_cleaned_data()
        client = APIClient()
        client.credentials(HTTP_X_USER_ID="abc")

        resp = client.get(f"/api/collections/cleaned-data/{cleaned.id}/download/structured/")

        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_download_cleaned_csv_permission_denied(self, create_collection, create_cleaned_data):
        other_collection = create_collection(user_id=2, repository_id=333, status="completed")
        cleaned = create_cleaned_data(collection=other_collection)

        resp = _auth_client().get(f"/api/collections/cleaned-data/{cleaned.id}/download/structured/")

        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_download_cleaned_csv_invalid_type(self, create_cleaned_data):
        cleaned = create_cleaned_data()

        resp = _auth_client().get(f"/api/collections/cleaned-data/{cleaned.id}/download/unknown/")

        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_download_cleaned_csv_missing_filename(self, create_cleaned_data):
        cleaned = create_cleaned_data(structured_csv_filename="")

        resp = _auth_client().get(f"/api/collections/cleaned-data/{cleaned.id}/download/structured/")

        assert resp.status_code == status.HTTP_404_NOT_FOUND

    @patch("collectors.api.views.CleanedDataService.get_csv_for_download", return_value=None)
    def test_download_cleaned_csv_missing_storage_file(self, _mock_service, create_cleaned_data):
        cleaned = create_cleaned_data(structured_csv_filename="structured.csv")

        resp = _auth_client().get(f"/api/collections/cleaned-data/{cleaned.id}/download/structured/")

        assert resp.status_code == status.HTTP_404_NOT_FOUND

    @patch("collectors.api.views.CleanedDataService.get_csv_for_download", side_effect=CollectionValidationError("bad type"))
    def test_download_cleaned_csv_validation_error(self, _mock_service, create_cleaned_data):
        cleaned = create_cleaned_data(structured_csv_filename="structured.csv")

        resp = _auth_client().get(f"/api/collections/cleaned-data/{cleaned.id}/download/structured/")

        assert resp.status_code == status.HTTP_400_BAD_REQUEST


# ---------------------------------------------------------------------------
# External uploads and analysis datasets
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestUploadExternalCollectionView:
    def test_upload_requires_file(self):
        resp = _auth_client().post("/api/collections/upload-external/", {"platform": "github"})

        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_upload_rejects_unknown_platform(self):
        upload = SimpleUploadedFile("data.json", b'{"pull_requests": []}', content_type="application/json")

        resp = _auth_client().post(
            "/api/collections/upload-external/",
            {"platform": "bitbucket", "name": "repo", "file": upload},
            format="multipart",
        )

        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_upload_rejects_invalid_json_shape(self):
        upload = SimpleUploadedFile("data.json", b"not-json", content_type="application/json")

        resp = _auth_client().post(
            "/api/collections/upload-external/",
            {"platform": "github", "name": "repo", "file": upload},
            format="multipart",
        )

        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    @patch("collectors.minio_client.MinIOClient")
    def test_upload_storage_failure_deletes_collection(self, mock_minio_cls):
        minio = MagicMock()
        minio.generate_filename.return_value = "external.json"
        minio.save_stream.return_value = False
        mock_minio_cls.return_value = minio
        upload = SimpleUploadedFile("data.json", b'{"pull_requests": []}', content_type="application/json")

        resp = _auth_client().post(
            "/api/collections/upload-external/",
            {"platform": "github", "name": "repo", "file": upload},
            format="multipart",
        )

        assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert not Collection.objects.filter(repository_full_name="external/repo").exists()

    @patch("collectors.metadata_extractor.extract_cleaning_metadata", return_value={"total_items": 3})
    @patch("collectors.minio_client.MinIOClient")
    def test_upload_success_extracts_metadata(self, mock_minio_cls, mock_extract):
        minio = MagicMock()
        minio.generate_filename.return_value = "external.json"
        minio.save_stream.return_value = True
        stream = MagicMock()
        minio.get_object_stream.return_value = stream
        mock_minio_cls.return_value = minio
        upload = SimpleUploadedFile("data.json", b'{"pull_requests": []}', content_type="application/json")

        resp = _auth_client().post(
            "/api/collections/upload-external/",
            {"platform": "github", "name": "repo", "file": upload},
            format="multipart",
        )

        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["success"] is True
        collection = Collection.objects.get(repository_full_name="external/repo")
        assert collection.raw_data_filename == "external.json"
        assert collection.total_items == 3
        mock_extract.assert_called_once_with(stream, "github")
        stream.close.assert_called_once()
        stream.release_conn.assert_called_once()

    @patch("collectors.metadata_extractor.extract_cleaning_metadata", side_effect=RuntimeError("bad metadata"))
    @patch("collectors.minio_client.MinIOClient")
    def test_upload_metadata_failure_is_non_fatal(self, mock_minio_cls, _mock_extract):
        minio = MagicMock()
        minio.generate_filename.return_value = "external.json"
        minio.save_stream.return_value = True
        minio.get_object_stream.return_value = MagicMock()
        mock_minio_cls.return_value = minio
        upload = SimpleUploadedFile("data.json", b'{"merge_requests": []}', content_type="application/json")

        resp = _auth_client().post(
            "/api/collections/upload-external/",
            {"platform": "gitlab", "name": "gitlab-repo", "file": upload},
            format="multipart",
        )

        assert resp.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
class TestDatasetViews:
    def test_cleaned_for_analysis_filters_search_and_requires_statistics(self, create_collection, create_cleaned_data):
        matching = create_collection(status="completed", repository_id=600, repository_name="analytics-api")
        create_cleaned_data(collection=matching, statistics_csv_filename="stats.csv", status="completed")
        ignored = create_collection(status="completed", repository_id=601, repository_name="other-api")
        create_cleaned_data(collection=ignored, statistics_csv_filename="", status="completed")

        resp = _auth_client().get("/api/collections/cleaned-for-analysis/?search=analytics")

        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["count"] == 1
        assert resp.data["results"][0]["repository_name"] == "analytics-api"

    @patch("collectors.api.views.UserDatasetsService.get_user_datasets", return_value={"collections": [], "summary": {}})
    def test_user_datasets_success(self, mock_service):
        resp = _auth_client().get("/api/collections/datasets/")

        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["collections"] == []
        mock_service.assert_called_once_with(1)

    @patch("collectors.api.views.UserDatasetsService.get_user_datasets", side_effect=ValueError("bad id"))
    def test_user_datasets_value_error(self, _mock_service):
        resp = _auth_client().get("/api/collections/datasets/")

        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    @patch("collectors.api.views.UserDatasetsService.get_user_datasets", side_effect=RuntimeError("db down"))
    def test_user_datasets_unexpected_error(self, _mock_service):
        resp = _auth_client().get("/api/collections/datasets/")

        assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


# ---------------------------------------------------------------------------
# Serializer validation
# ---------------------------------------------------------------------------

class TestStartCollectionSerializer:
    def test_valid_data(self):
        from collectors.api.serializers import StartCollectionSerializer

        s = StartCollectionSerializer(
            data={
                "repository_id": 1,
                "workspace_id": 1,
                "repository_name": "repo",
                "repository_full_name": "o/repo",
                "platform": "github",
            }
        )
        assert s.is_valid(), s.errors

    def test_missing_platform(self):
        from collectors.api.serializers import StartCollectionSerializer

        s = StartCollectionSerializer(
            data={"repository_id": 1, "workspace_id": 1, "repository_name": "r", "repository_full_name": "o/r"}
        )
        assert not s.is_valid()
        assert "platform" in s.errors


class TestMetricsFilterSerializer:
    def test_valid(self):
        from collectors.api.serializers import MetricsFilterSerializer

        s = MetricsFilterSerializer(
            data={"selected_metrics": ["pr_title"], "start_date": "2024-01-01"}
        )
        assert s.is_valid(), s.errors

    def test_empty_metrics_is_invalid(self):
        from collectors.api.serializers import MetricsFilterSerializer

        s = MetricsFilterSerializer(data={"selected_metrics": []})
        assert not s.is_valid()

    def test_end_before_start_invalid(self):
        from collectors.api.serializers import MetricsFilterSerializer

        s = MetricsFilterSerializer(
            data={
                "selected_metrics": ["pr_title"],
                "start_date": "2024-12-01",
                "end_date": "2024-01-01",
            }
        )
        assert not s.is_valid()
