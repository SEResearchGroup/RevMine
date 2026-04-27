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

from collectors.models import Collection


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
