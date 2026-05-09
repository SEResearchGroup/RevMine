"""
Infrastructure – Celery Tasks
===============================
Async Celery tasks for analysis processing. These are thin wrappers that
delegate all business logic to the service layer. Keep infrastructure concerns
(task routing, retries, scheduling) here and nothing else.
"""
from __future__ import annotations

import logging
import time
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
    _start = time.monotonic()
    try:
        analysis = Analysis.objects.get(id=analysis_id)
        logger.info(
            "Celery analysis task started",
            extra={
                "analysis_id": str(analysis_id),
                "metric": getattr(analysis, "metric_code", None),
                "dataset_id": str(getattr(analysis, "dataset_id", "")),
                "event": "celery_analysis_started",
                "status": "started",
            },
        )
        service = AnalysisService()
        service.process_analysis(analysis)
        _duration = round(time.monotonic() - _start, 3)
        logger.info(
            "Celery analysis task completed",
            extra={
                "analysis_id": str(analysis_id),
                "metric": getattr(analysis, "metric_code", None),
                "duration": _duration,
                "status": "success",
                "event": "celery_analysis_completed",
            },
        )
        return {
            "status": "success",
            "analysis_id": str(analysis_id),
            "message": "Analysis completed successfully",
            "duration": _duration,
        }
    except Analysis.DoesNotExist:
        logger.warning(
            "Analysis not found in Celery task",
            extra={"analysis_id": str(analysis_id), "status": "error", "event": "analysis_not_found"},
        )
        return {
            "status": "error",
            "analysis_id": str(analysis_id),
            "message": "Analysis not found",
        }
    except Exception as exc:
        _duration = round(time.monotonic() - _start, 3)
        logger.exception(
            "Celery task process_analysis failed",
            extra={
                "analysis_id": str(analysis_id),
                "status": "failed",
                "error": str(exc),
                "duration": _duration,
                "event": "celery_analysis_failed",
            },
        )
        return {
            "status": "error",
            "analysis_id": str(analysis_id),
            "message": str(exc),
            "duration": _duration,
        }


@shared_task
def process_batch(batch_id: str) -> dict:
    """
    Process all analyses in a batch, tracking per-analysis progress.
    Delegates each analysis to AnalysisService.
    """
    _start = time.monotonic()
    try:
        batch = AnalysisBatch.objects.get(id=batch_id)
        batch.status = "processing"
        batch.save()

        analyses_count = batch.batch_analyses.count()
        logger.info(
            "Celery batch task started",
            extra={
                "batch_id": str(batch_id),
                "analyses_count": analyses_count,
                "status": "started",
                "event": "celery_batch_started",
            },
        )

        for batch_analysis in batch.batch_analyses.select_related("analysis").order_by("id"):
            analysis = batch_analysis.analysis
            process_analysis.delay(str(analysis.id))

        batch.completed_at = timezone.now()
        batch.save()

        _duration = round(time.monotonic() - _start, 3)
        logger.info(
            "Celery batch task dispatched",
            extra={
                "batch_id": str(batch_id),
                "completed": batch.completed_analyses,
                "failed": batch.failed_analyses,
                "duration": _duration,
                "status": "success",
                "event": "celery_batch_dispatched",
            },
        )
        return {
            "status": "success",
            "batch_id": str(batch_id),
            "completed": batch.completed_analyses,
            "failed": batch.failed_analyses,
            "duration": _duration,
        }
    except AnalysisBatch.DoesNotExist:
        logger.warning(
            "Batch not found in Celery task",
            extra={"batch_id": str(batch_id), "status": "error", "event": "batch_not_found"},
        )
        return {
            "status": "error",
            "batch_id": str(batch_id),
            "message": "Batch not found",
        }
    except Exception as exc:
        _duration = round(time.monotonic() - _start, 3)
        logger.exception(
            "Celery task process_batch failed",
            extra={
                "batch_id": str(batch_id),
                "status": "failed",
                "error": str(exc),
                "duration": _duration,
                "event": "celery_batch_failed",
            },
        )
        return {
            "status": "error",
            "batch_id": str(batch_id),
            "message": str(exc),
            "duration": _duration,
        }


@shared_task
def cleanup_old_analyses(days: int = 30) -> dict:
    """
    Periodic maintenance task: delete completed/failed analyses older than
    ``days`` days.
    """
    _start = time.monotonic()
    cutoff_date = timezone.now() - timedelta(days=days)
    deleted_count, _ = Analysis.objects.filter(
        created_at__lt=cutoff_date,
        status__in=["completed", "failed"],
    ).delete()

    _duration = round(time.monotonic() - _start, 3)
    logger.info(
        "Old analyses cleanup completed",
        extra={
            "deleted_count": deleted_count,
            "retention_days": days,
            "duration": _duration,
            "status": "success",
            "event": "analyses_cleanup_completed",
        },
    )
    return {
        "status": "success",
        "deleted_count": deleted_count,
        "message": f"Deleted analyses older than {days} days",
        "duration": _duration,
    }
