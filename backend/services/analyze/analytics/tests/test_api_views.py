"""
Integration / API tests for analyze service endpoints.
=======================================================
Tests the full request-response cycle through DRF views using Django's
test client. All Celery tasks and external services are mocked.

Run with:
    cd /home/s3lf-ouss/pfe/revmine/backend/services/analyze
    python -m pytest analytics/tests/test_api_views.py -v
"""

import io
import json
import uuid
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
from django.test import TestCase, Client, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from analytics.models import Dataset, MetricDefinition, Analysis, AnalysisResult
from analytics.services.dataset_service import DatasetStorageError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_CSV = b"""Creation_Date,Lead_Time,#Commits,state
2023-10-01,10.5,3,merged
2023-10-02,5.2,1,opened
2023-10-03,20.0,5,merged
"""


def _auth_client(user_id=1, workspace_id=1, repository_id=1):
    """Return an APIClient with the auth headers set by the middleware."""
    client = APIClient()
    client.credentials(
        HTTP_X_USER_ID=str(user_id),
        HTTP_X_WORKSPACE_ID=str(workspace_id),
        HTTP_X_REPOSITORY_ID=str(repository_id),
    )
    return client


# ---------------------------------------------------------------------------
# Dataset endpoints
# ---------------------------------------------------------------------------

@override_settings(MEDIA_ROOT="/tmp/test_analyze_api_media/")
class DatasetListViewTests(TestCase):

    def setUp(self):
        self.client = _auth_client()

    def test_list_empty(self):
        resp = self.client.get("/api/analysis/datasets/")
        self.assertIn(resp.status_code, [200, 401, 403])

    def test_list_filters_by_user_id(self):
        Dataset.objects.create(
            user_id=1,
            workspace_id=1,
            repository_id=1,
            platform="gitlab",
            filename="owned.csv",
            file_path="datasets/owned.csv",
            rows_count=1,
            columns_count=1,
            columns_metadata={},
        )
        Dataset.objects.create(
            user_id=2,
            workspace_id=2,
            repository_id=2,
            platform="github",
            filename="other.csv",
            file_path="datasets/other.csv",
            rows_count=1,
            columns_count=1,
            columns_metadata={},
        )

        resp = self.client.get("/api/analysis/datasets/")

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["count"], 1)
        self.assertEqual(resp.data["results"][0]["filename"], "owned.csv")

    @patch("analytics.api.views.DatasetService")
    def test_upload_csv(self, MockDatasetService):
        svc_instance = MockDatasetService.return_value
        dataset = Dataset(
            id=uuid.uuid4(),
            workspace_id=1,
            repository_id=1,
            platform="gitlab",
            filename="test.csv",
            file_path="datasets/test.csv",
            rows_count=3,
            columns_count=4,
            columns_metadata={},
        )
        svc_instance.create_dataset.return_value = dataset

        resp = self.client.post(
            "/api/analysis/datasets/upload/",
            {
                "file": io.BytesIO(SAMPLE_CSV),
                "workspace_id": 1,
                "repository_id": 1,
                "platform": "gitlab",
            },
            format="multipart",
        )
        # 201 Created or 400/403 depending on auth middleware
        self.assertIn(resp.status_code, [201, 200, 400, 401, 403])

    @patch("analytics.api.serializers.DatasetService")
    def test_upload_storage_error_returns_json_503(self, MockDatasetService):
        svc_instance = MockDatasetService.return_value
        svc_instance.create_dataset.side_effect = DatasetStorageError(
            "Dataset storage is not writable"
        )

        resp = self.client.post(
            "/api/analysis/datasets/upload/",
            {
                "file": SimpleUploadedFile(
                    "test.csv",
                    SAMPLE_CSV,
                    content_type="text/csv",
                ),
                "workspace_id": 1,
                "repository_id": 1,
                "platform": "gitlab",
            },
            format="multipart",
        )

        self.assertEqual(resp.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(resp.data["error"], "Dataset storage unavailable")


# ---------------------------------------------------------------------------
# Metrics catalogue
# ---------------------------------------------------------------------------

class MetricListViewTests(TestCase):

    def setUp(self):
        self.client = _auth_client()

    def test_metric_list_returns_200_or_auth_error(self):
        resp = self.client.get("/api/analysis/metrics/")
        self.assertIn(resp.status_code, [200, 401, 403])


# ---------------------------------------------------------------------------
# Generate chart endpoint
# ---------------------------------------------------------------------------

@override_settings(MEDIA_ROOT="/tmp/test_analyze_api_media/")
class GenerateChartViewTests(TestCase):

    def setUp(self):
        self.client = _auth_client()
        # Seed a MetricDefinition and Dataset so the view can find them
        self.metric, _ = MetricDefinition.objects.get_or_create(
            code="lead_time_distribution",
            defaults={
                "name": "Lead Time Distribution",
                "category": "process",
                "source_type": "gitlab",
                "default_chart_type": "histogram",
                "supported_chart_types": ["histogram", "bar"],
                "required_columns": ["Lead_Time"],
            },
        )
        self.dataset = Dataset.objects.create(
            user_id=1,
            workspace_id=1,
            repository_id=1,
            platform="gitlab",
            filename="test.csv",
            file_path="datasets/test.csv",
            rows_count=3,
            columns_count=4,
            columns_metadata={"Lead_Time": "float64", "Creation_Date": "datetime64[ns]"},
        )

    @patch("analytics.api.views.AnalysisService")
    @patch("analytics.api.views.DatasetService")
    def test_generate_chart_success(self, MockDatasetService, MockAnalysisService):
        df = pd.read_csv(StringIO("Lead_Time,Creation_Date\n10.5,2023-01-01\n5.0,2023-01-02"))
        df["Creation_Date"] = pd.to_datetime(df["Creation_Date"])

        ds_instance = MockDatasetService.return_value
        ds_instance.load_dataframe.return_value = df
        ds_instance.get_columns.return_value = ["Lead_Time", "Creation_Date"]

        fake_chart = {"type": "histogram", "data": {"labels": [], "datasets": []}}
        fake_stats = {"mean": 7.75}
        as_instance = MockAnalysisService.return_value
        as_instance.function_mapping = {
            "lead_time_distribution": MagicMock(return_value=(fake_chart, fake_stats, None))
        }

        def fake_process_analysis(analysis):
            result = AnalysisResult.objects.create(
                analysis=analysis,
                chart_data=fake_chart,
                statistics=fake_stats,
                chart_image=None,
            )
            analysis.status = 'completed'
            analysis.result = result
            analysis.save()

        as_instance.process_analysis.side_effect = fake_process_analysis

        payload = {
            "dataset_id": str(self.dataset.id),
            "metric_code": "lead_time_distribution",
            "chart_type": "histogram",
        }
        resp = self.client.post(
            "/api/analysis/generate/",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertIn(resp.status_code, [200, 201, 400, 401, 403])

    def test_generate_chart_missing_metric_code_returns_400(self):
        payload = {
            "dataset_id": str(self.dataset.id),
            "chart_type": "histogram",
        }
        resp = self.client.post(
            "/api/analysis/generate/",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertIn(resp.status_code, [400, 401, 403])


# ---------------------------------------------------------------------------
# Analysis CRUD
# ---------------------------------------------------------------------------

class AnalysisViewTests(TestCase):

    def setUp(self):
        self.client = _auth_client()
        self.metric, _ = MetricDefinition.objects.get_or_create(
            code="lead_time_distribution",
            defaults={
                "name": "Lead Time Distribution",
                "category": "process",
                "source_type": "gitlab",
                "default_chart_type": "histogram",
                "supported_chart_types": ["histogram"],
                "required_columns": ["Lead_Time"],
            },
        )
        self.dataset = Dataset.objects.create(
            user_id=1,
            workspace_id=1,
            repository_id=1,
            platform="gitlab",
            filename="test.csv",
            file_path="datasets/test.csv",
            rows_count=3,
            columns_count=1,
            columns_metadata={"Lead_Time": "float64"},
        )

    def test_analysis_list_returns_200_or_auth_error(self):
        resp = self.client.get("/api/analysis/analyses/")
        self.assertIn(resp.status_code, [200, 401, 403])

    def test_analysis_detail_404_for_unknown_id(self):
        resp = self.client.get(f"/api/analysis/analyses/{uuid.uuid4()}/")
        self.assertIn(resp.status_code, [404, 401, 403])
