"""
Tests for backward-compatibility shims.
========================================
Verifies that all old flat import paths still resolve to the correct classes
in the new layered architecture. This ensures zero breaking changes.

Run with:
    cd /home/s3lf-ouss/pfe/revmine/backend/services/analyze
    python -m pytest analytics/tests/test_shim_compatibility.py -v
"""

from django.test import SimpleTestCase


class ShimImportTests(SimpleTestCase):
    """All old module paths must export the same objects as the new locations."""

    def test_analysis_service_shim(self):
        from analytics.analysis_service import AnalysisService as ShimClass
        from analytics.services.analysis_service import AnalysisService as RealClass
        self.assertIs(ShimClass, RealClass)

    def test_dataset_services_shim(self):
        from analytics.dataset_services import DatasetService as ShimClass
        from analytics.services.dataset_service import DatasetService as RealClass
        self.assertIs(ShimClass, RealClass)

    def test_kafka_handlers_shim(self):
        from analytics.kafka_handlers import start_kafka_consumers as shim_fn
        from analytics.infrastructure.messaging.kafka_handlers import (
            start_kafka_consumers as real_fn,
        )
        self.assertIs(shim_fn, real_fn)

    def test_tasks_shim_process_analysis(self):
        from analytics.tasks import process_analysis as shim_fn
        from analytics.infrastructure.tasks.celery_tasks import (
            process_analysis as real_fn,
        )
        self.assertIs(shim_fn, real_fn)

    def test_tasks_shim_process_batch(self):
        from analytics.tasks import process_batch as shim_fn
        from analytics.infrastructure.tasks.celery_tasks import process_batch as real_fn
        self.assertIs(shim_fn, real_fn)

    def test_devops_collectors_shim(self):
        from analytics.devops_collectors import GitHubActionsCollector as ShimClass
        from analytics.infrastructure.collectors.devops_collectors import (
            GitHubActionsCollector as RealClass,
        )
        self.assertIs(ShimClass, RealClass)

    def test_devops_tasks_shim(self):
        from analytics.devops_tasks import start_job as shim_fn
        from analytics.infrastructure.tasks.devops_tasks import start_job as real_fn
        self.assertIs(shim_fn, real_fn)

    def test_serializers_shim(self):
        from analytics.serializers import DatasetSerializer as ShimClass
        from analytics.api.serializers import DatasetSerializer as RealClass
        self.assertIs(ShimClass, RealClass)

    def test_views_shim(self):
        from analytics.views import GenerateChartView as ShimClass
        from analytics.api.views import GenerateChartView as RealClass
        self.assertIs(ShimClass, RealClass)

    def test_devops_views_shim(self):
        from analytics.devops_views import KanbanCollectView as ShimClass
        from analytics.api.devops_views import KanbanCollectView as RealClass
        self.assertIs(ShimClass, RealClass)

    def test_urls_shim(self):
        from analytics.urls import urlpatterns as shim_patterns
        from analytics.api.urls import urlpatterns as real_patterns
        self.assertIs(shim_patterns, real_patterns)

    def test_analysis_functions_shim(self):
        """Functions from the old module should be accessible via shim."""
        # Importing the shim should not raise
        import analytics.analysis_functions  # noqa: F401
