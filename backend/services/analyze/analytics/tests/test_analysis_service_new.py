"""
Unit tests for AnalysisService (service layer).
================================================
Tests the slim orchestration layer: process_analysis, function_mapping
delegation to MetricsEngine, and result persistence.

Run with:
    cd /home/s3lf-ouss/pfe/revmine/backend/services/analyze
    python -m pytest analytics/tests/test_analysis_service_new.py -v
"""

import uuid
from io import StringIO
from unittest.mock import MagicMock, patch, call

import pandas as pd
import pytest
from django.test import TestCase

from analytics.services.analysis_service import AnalysisService
from analytics.domain.metrics.metrics_engine import MetricsEngine
from analytics.models import Dataset, MetricDefinition, Analysis, AnalysisResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_CSV = """\
Creation_Date,Lead_Time,#Commits,state
2023-10-01,10.5,3,merged
2023-10-02,5.2,1,opened
2023-10-03,20.0,5,merged
"""


def _make_analysis(metric_code="lead_time_distribution", chart_type="histogram"):
    dataset = Dataset(
        id=uuid.uuid4(),
        workspace_id=1,
        repository_id=1,
        platform="gitlab",
        filename="test.csv",
        file_path="datasets/test.csv",
        columns_metadata={"Creation_Date": "datetime64[ns]", "Lead_Time": "float64"},
    )
    metric = MetricDefinition(
        code=metric_code,
        name="Lead Time Distribution",
        required_columns=["Lead_Time"],
        supported_chart_types=[chart_type],
    )
    analysis = Analysis(
        id=uuid.uuid4(),
        dataset=dataset,
        metric_code=metric_code,
        chart_type=chart_type,
        config={},
        status="pending",
    )
    # Attach mock metric lookup
    analysis._metric = metric
    return analysis, dataset


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class AnalysisServiceInitTests(TestCase):
    """AnalysisService wraps MetricsEngine and exposes function_mapping."""

    def test_instantiation(self):
        svc = AnalysisService()
        self.assertIsInstance(svc, AnalysisService)

    def test_has_engine(self):
        svc = AnalysisService()
        self.assertIsInstance(svc._engine, MetricsEngine)

    def test_function_mapping_mirrors_engine(self):
        svc = AnalysisService()
        self.assertEqual(svc.function_mapping, svc._engine.function_mapping)

    def test_function_mapping_not_empty(self):
        svc = AnalysisService()
        self.assertGreater(len(svc.function_mapping), 0)


class AnalysisServiceProcessTests(TestCase):
    """process_analysis orchestrates loading, computing, and saving."""

    @patch("analytics.services.analysis_service.AnalysisResult")
    @patch("analytics.services.analysis_service.MetricDefinition")
    @patch("analytics.services.analysis_service.DatasetService")
    def test_process_analysis_success(
        self, MockDatasetService, MockMetricDefinition, MockAnalysisResult
    ):
        analysis, dataset = _make_analysis()

        # DatasetService mock
        svc_instance = MockDatasetService.return_value
        df = pd.read_csv(StringIO(SAMPLE_CSV))
        df["Creation_Date"] = pd.to_datetime(df["Creation_Date"])
        svc_instance.load_dataframe.return_value = df

        # MetricDefinition mock
        metric = MagicMock()
        metric.required_columns = ["Lead_Time"]
        MockMetricDefinition.objects.get.return_value = metric

        # Mock the engine function
        fake_chart = {"type": "histogram", "data": {"labels": [], "datasets": []}}
        fake_stats = {"mean": 12.0}
        fake_engine_fn = MagicMock(return_value=(fake_chart, fake_stats, None))

        # analysis.save mock
        analysis.save = MagicMock()

        result_instance = MagicMock()
        MockAnalysisResult.objects.update_or_create.return_value = (result_instance, True)

        # Patch the engine's function_mapping
        with patch.object(
            AnalysisService,
            "function_mapping",
            new_callable=lambda: property(lambda self: {"lead_time_distribution": fake_engine_fn}),
        ):
            service = AnalysisService()
            service.process_analysis(analysis)

        analysis.save.assert_called()
        # analysis status should be completed
        self.assertEqual(analysis.status, "completed")

    @patch("analytics.services.analysis_service.MetricDefinition")
    @patch("analytics.services.analysis_service.DatasetService")
    def test_process_analysis_unknown_metric_sets_failed(
        self, MockDatasetService, MockMetricDefinition
    ):
        analysis, dataset = _make_analysis(metric_code="nonexistent_metric")

        svc_instance = MockDatasetService.return_value
        df = pd.read_csv(StringIO(SAMPLE_CSV))
        svc_instance.load_dataframe.return_value = df

        MockMetricDefinition.objects.get.side_effect = MetricDefinition.DoesNotExist

        analysis.save = MagicMock()

        service = AnalysisService()
        service.process_analysis(analysis)

        self.assertEqual(analysis.status, "failed")
        self.assertIsNotNone(analysis.error_message)

    @patch("analytics.services.analysis_service.MetricDefinition")
    @patch("analytics.services.analysis_service.DatasetService")
    def test_process_analysis_exception_sets_failed(
        self, MockDatasetService, MockMetricDefinition
    ):
        analysis, dataset = _make_analysis()

        svc_instance = MockDatasetService.return_value
        svc_instance.load_dataframe.side_effect = RuntimeError("disk read error")

        MockMetricDefinition.objects.get.return_value = MagicMock(required_columns=["Lead_Time"])
        analysis.save = MagicMock()

        service = AnalysisService()
        service.process_analysis(analysis)

        self.assertEqual(analysis.status, "failed")
        self.assertIn("disk read error", analysis.error_message)
