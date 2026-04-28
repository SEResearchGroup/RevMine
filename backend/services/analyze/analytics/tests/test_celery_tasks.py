"""
Unit tests for Celery tasks (infrastructure/tasks layer).
=========================================================
Tasks are tested with all DB and service calls mocked so no broker is needed.

Run with:
    cd /home/s3lf-ouss/pfe/revmine/backend/services/analyze
    python -m pytest analytics/tests/test_celery_tasks.py -v
"""

import uuid
from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.utils import timezone

from analytics.infrastructure.tasks.celery_tasks import (
    process_analysis,
    process_batch,
    cleanup_old_analyses,
)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class ProcessAnalysisTaskTests(TestCase):

    @patch("analytics.infrastructure.tasks.celery_tasks.AnalysisService")
    @patch("analytics.infrastructure.tasks.celery_tasks.Analysis")
    def test_process_analysis_calls_service(self, MockAnalysis, MockAnalysisService):
        analysis_id = str(uuid.uuid4())
        analysis = MagicMock()
        MockAnalysis.objects.get.return_value = analysis
        svc = MockAnalysisService.return_value

        process_analysis(analysis_id)

        MockAnalysis.objects.get.assert_called_once_with(id=analysis_id)
        svc.process_analysis.assert_called_once_with(analysis)

    @patch("analytics.infrastructure.tasks.celery_tasks.Analysis")
    def test_process_analysis_missing_id_does_not_raise(self, MockAnalysis):
        from analytics.models import Analysis as RealAnalysis
        MockAnalysis.objects.get.side_effect = RealAnalysis.DoesNotExist
        # Should not propagate the exception
        process_analysis(str(uuid.uuid4()))


class ProcessBatchTaskTests(TestCase):

    @patch("analytics.infrastructure.tasks.celery_tasks.process_analysis")
    @patch("analytics.infrastructure.tasks.celery_tasks.AnalysisBatch")
    def test_process_batch_dispatches_per_analysis(self, MockBatch, mock_process_analysis):
        batch_id = str(uuid.uuid4())
        batch = MagicMock()
        batch.status = "pending"
        batch.total_analyses = 3

        a1, a2, a3 = MagicMock(), MagicMock(), MagicMock()
        a1.id, a2.id, a3.id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()

        ba1, ba2, ba3 = MagicMock(), MagicMock(), MagicMock()
        ba1.analysis, ba2.analysis, ba3.analysis = a1, a2, a3
        batch.batch_analyses.select_related.return_value.order_by.return_value = [
            ba1, ba2, ba3
        ]

        MockBatch.objects.get.return_value = batch

        process_batch(batch_id)

        self.assertEqual(mock_process_analysis.delay.call_count, 3)

    @patch("analytics.infrastructure.tasks.celery_tasks.AnalysisBatch")
    def test_process_batch_missing_id_does_not_raise(self, MockBatch):
        from analytics.models import AnalysisBatch as RealBatch
        MockBatch.objects.get.side_effect = RealBatch.DoesNotExist
        process_batch(str(uuid.uuid4()))


class CleanupOldAnalysesTests(TestCase):

    @patch("analytics.infrastructure.tasks.celery_tasks.Analysis")
    def test_cleanup_deletes_old_completed(self, MockAnalysis):
        qs = MagicMock()
        qs.count.return_value = 5
        MockAnalysis.objects.filter.return_value = qs

        cleanup_old_analyses()

        MockAnalysis.objects.filter.assert_called_once()
        qs.delete.assert_called_once()
