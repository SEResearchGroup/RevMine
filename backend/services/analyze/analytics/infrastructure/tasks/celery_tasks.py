"""
Infrastructure – Celery Tasks
===============================
Async Celery tasks for analysis processing. These are thin wrappers that
delegate all business logic to the service layer. Keep infrastructure concerns
(task routing, retries, scheduling) here and nothing else.
"""
from __future__ import annotations

import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from analytics.models import Analysis, AnalysisBatch
from analytics.services.analysis_service import AnalysisService

logger = logging.getLogger(__name__)


@shared_task
def process_analysis(analysis_id: str) -> dict:
    """
    Process a single analysis asynchronously.
    Delegates to AnalysisService for all business logic.
    """
    try:
        analysis = Analysis.objects.get(id=analysis_id)
        service = AnalysisService()
        service.process_analysis(analysis)
        return {
            "status": "success",
            "analysis_id": str(analysis_id),
            "message": "Analysis completed successfully",
        }
    except Analysis.DoesNotExist:
        return {
            "status": "error",
            "analysis_id": str(analysis_id),
            "message": "Analysis not found",
        }
    except Exception as exc:
        logger.exception("Celery task process_analysis failed for %s", analysis_id)
        return {
            "status": "error",
            "analysis_id": str(analysis_id),
            "message": str(exc),
        }


@shared_task
def process_batch(batch_id: str) -> dict:
    """
    Process all analyses in a batch, tracking per-analysis progress.
    Delegates each analysis to AnalysisService.
    """
    try:
        batch = AnalysisBatch.objects.get(id=batch_id)
        batch.status = "processing"
        batch.save()

        for batch_analysis in batch.batch_analyses.select_related("analysis").order_by("id"):
            analysis = batch_analysis.analysis
            process_analysis.delay(str(analysis.id))

        batch.completed_at = timezone.now()
        batch.save()

        return {
            "status": "success",
            "batch_id": str(batch_id),
            "completed": batch.completed_analyses,
            "failed": batch.failed_analyses,
        }
    except AnalysisBatch.DoesNotExist:
        return {
            "status": "error",
            "batch_id": str(batch_id),
            "message": "Batch not found",
        }
    except Exception as exc:
        logger.exception("Celery task process_batch failed for %s", batch_id)
        return {
            "status": "error",
            "batch_id": str(batch_id),
            "message": str(exc),
        }


@shared_task
def cleanup_old_analyses(days: int = 30) -> dict:
    """
    Periodic maintenance task: delete completed/failed analyses older than
    ``days`` days.
    """
    cutoff_date = timezone.now() - timedelta(days=days)
    deleted_count, _ = Analysis.objects.filter(
        created_at__lt=cutoff_date,
        status__in=["completed", "failed"],
    ).delete()

    return {
        "status": "success",
        "deleted_count": deleted_count,
        "message": f"Deleted analyses older than {days} days",
    }
