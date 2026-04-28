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

logger = logging.getLogger(__name__)


@shared_task
def process_analysis(analysis_id: str) -> dict:
    """
    Process a single analysis asynchronously.
    Delegates to AnalysisService for all business logic.
    """
    from analytics.models import Analysis
    from analytics.services.analysis_service import AnalysisService

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
    from analytics.models import AnalysisBatch
    from analytics.services.analysis_service import AnalysisService

    try:
        batch = AnalysisBatch.objects.get(id=batch_id)
        batch.status = "processing"
        batch.save()

        for batch_analysis in batch.batch_analyses.all():
            analysis = batch_analysis.analysis
            try:
                service = AnalysisService()
                service.process_analysis(analysis)
                batch.completed_analyses += 1
            except Exception as exc:
                logger.warning("Batch %s: analysis %s failed: %s", batch_id, analysis.id, exc)
                batch.failed_analyses += 1
            batch.save()

        # Determine final batch status
        if batch.failed_analyses == 0:
            batch.status = "completed"
        elif batch.completed_analyses > 0:
            batch.status = "partial"
        else:
            batch.status = "failed"

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
    from analytics.models import Analysis

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
