"""
Background runners for Kanban / CI-CD collections.

Mirror of `backend/services/collection/collectors/tasks.py`: spawn a daemon
thread on request, persist progress against a `DevOpsCollectionJob` row, and
publish a Kafka notification when the job finishes (success or failure) so the
notification service can fan it out over WebSocket.

Kept intentionally simple — no Celery dependency, no MinIO. The collectors
themselves are paginated HTTP loops and finish in seconds-to-minutes.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from typing import Optional

from django.utils import timezone

from analytics.services.dataset_service import DatasetService
from analytics.infrastructure.collectors.devops_collectors import (
    GitHubActionsCollector,
    GitHubProjectsCollector,
    GitLabBoardsCollector,
    GitLabCICollector,
)
from analytics.models import DevOpsCollectionJob

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def start_job(job: DevOpsCollectionJob, token: str) -> None:
    """Spawn the background worker. Token is passed in-memory only."""
    thread = threading.Thread(
        target=_run_job,
        args=(str(job.id), token),
        daemon=True,
        name=f"devops-job-{job.id}",
    )
    thread.start()
    logger.info(
        "DevOps background job started",
        extra={
            "job_id": str(job.id),
            "source_type": job.source_type,
            "provider": job.provider,
            "repository_id": str(job.repository_id) if job.repository_id else None,
            "event": "devops_job_thread_started",
            "status": "started",
        },
    )


# ---------------------------------------------------------------------------
# Worker
# ---------------------------------------------------------------------------

def _run_job(job_id: str, token: str) -> None:
    job = DevOpsCollectionJob.objects.filter(id=job_id).first()
    if job is None:
        logger.warning(
            "DevOps job vanished before worker started",
            extra={"job_id": job_id, "event": "devops_job_not_found", "status": "error"},
        )
        return

    _start = time.monotonic()
    try:
        job.status = "in_progress"
        job.started_at = timezone.now()
        job.progress_percent = 5
        job.progress_message = "Connecting to provider…"
        job.save(update_fields=["status", "started_at", "progress_percent", "progress_message"])

        logger.info(
            "DevOps job worker running",
            extra={
                "job_id": job_id,
                "source_type": job.source_type,
                "provider": job.provider,
                "workspace_id": str(job.workspace_id) if job.workspace_id else None,
                "repository_id": str(job.repository_id) if job.repository_id else None,
                "status": "in_progress",
                "event": "devops_job_running",
            },
        )

        _publish_notification(job, "started")

        if job.source_type == "kanban":
            df = _run_kanban(job, token)
        elif job.source_type == "cicd":
            df = _run_cicd(job, token)
        else:
            raise ValueError(f"Unsupported source_type: {job.source_type}")

        if df is None or df.empty:
            raise RuntimeError("Provider returned no rows.")

        _set_progress(job, 80, "Saving dataset…")

        payload = job.request_payload or {}
        _save_start = time.monotonic()
        dataset = DatasetService().create_dataset_from_dataframe(
            df=df,
            filename=_filename_for_job(job, payload),
            source_type=job.source_type,
            source_config=_source_config_for_job(job, payload),
            collection_id=uuid.uuid4(),
            workspace_id=job.workspace_id,
            repository_id=job.repository_id,
            platform=job.provider,
        )
        _save_duration = round(time.monotonic() - _save_start, 3)

        job.refresh_from_db()
        job.dataset = dataset
        job.collected_items = int(getattr(dataset, "rows_count", 0) or 0)
        job.total_items = job.collected_items
        job.status = "completed"
        job.progress_percent = 100
        job.progress_message = "Collection complete."
        job.completed_at = timezone.now()
        job.save(
            update_fields=[
                "dataset",
                "collected_items",
                "total_items",
                "status",
                "progress_percent",
                "progress_message",
                "completed_at",
            ]
        )

        _total_duration = round(time.monotonic() - _start, 3)
        _publish_notification(job, "completed", dataset=dataset)
        logger.info(
            "DevOps job completed",
            extra={
                "job_id": job_id,
                "source_type": job.source_type,
                "provider": job.provider,
                "repository": str(job.repository_id) if job.repository_id else None,
                "dataset_id": str(dataset.id),
                "rows": job.collected_items,
                "duration": _total_duration,
                "save_duration": _save_duration,
                "status": "success",
                "event": "devops_job_completed",
            },
        )

    except Exception as exc:
        _total_duration = round(time.monotonic() - _start, 3)
        logger.exception(
            "DevOps job failed",
            extra={
                "job_id": job_id,
                "source_type": job.source_type if job else None,
                "provider": job.provider if job else None,
                "status": "failed",
                "error": str(exc),
                "duration": _total_duration,
                "event": "devops_job_failed",
            },
        )
        try:
            job.refresh_from_db()
            job.status = "failed"
            job.error_message = str(exc)
            job.completed_at = timezone.now()
            job.save(update_fields=["status", "error_message", "completed_at"])
        except Exception:
            pass
        _publish_notification(job, "failed", error=str(exc))


# ---------------------------------------------------------------------------
# Per-source runners
# ---------------------------------------------------------------------------

def _run_kanban(job: DevOpsCollectionJob, token: str):
    payload = job.request_payload or {}
    provider = (job.provider or payload.get("provider") or "").lower()
    board_id = payload.get("board_id")

    _set_progress(job, 25, f"Fetching board #{board_id} from {provider}…")

    if provider == "github":
        return GitHubProjectsCollector(token).collect_board(board_id)
    if provider == "gitlab":
        project_id = payload.get("project_id")
        base_url = payload.get("base_url") or "https://gitlab.com"
        return GitLabBoardsCollector(token, project_id, base_url).collect()

    raise ValueError(f"Unsupported provider: {provider}")


def _run_cicd(job: DevOpsCollectionJob, token: str):
    payload = job.request_payload or {}
    provider = (job.provider or payload.get("provider") or "").lower()

    if provider == "github":
        repo = payload.get("repo_full_name")
        if not repo:
            raise ValueError("repo_full_name is required for github CI/CD.")
        _set_progress(job, 25, f"Fetching workflow runs for {repo}…")
        return GitHubActionsCollector(token, repo).collect(
            since=payload.get("since"),
            max_runs=int(payload.get("max_runs") or 500),
        )

    if provider == "gitlab":
        project_id = payload.get("project_id")
        if not project_id:
            raise ValueError("project_id is required for gitlab CI/CD.")
        base_url = payload.get("base_url") or "https://gitlab.com"
        _set_progress(job, 25, f"Fetching pipelines for project {project_id}…")
        return GitLabCICollector(token, project_id, base_url).collect(
            max_pipelines=int(payload.get("max_runs") or 300),
        )

    raise ValueError(f"Unsupported provider: {provider}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _set_progress(job: DevOpsCollectionJob, percent: int, message: str) -> None:
    job.progress_percent = max(0, min(100, percent))
    job.progress_message = message[:255]
    job.save(update_fields=["progress_percent", "progress_message"])


def _filename_for_job(job: DevOpsCollectionJob, payload: dict) -> str:
    name = payload.get("name") or job.label or str(job.id)
    if job.source_type == "kanban":
        return f"kanban_{job.provider}_{name}.csv"
    if job.source_type == "cicd":
        return f"cicd_{job.provider}_{name}.csv"
    return f"{job.source_type}_{name}.csv"


def _source_config_for_job(job: DevOpsCollectionJob, payload: dict) -> dict:
    keys = ("provider", "board_id", "project_id", "owner", "base_url",
            "repo_full_name", "since", "workspace_id", "repository_id")
    cfg = {k: payload.get(k) for k in keys if payload.get(k) is not None}
    cfg.setdefault("provider", job.provider)
    return cfg


def _publish_notification(
    job: DevOpsCollectionJob,
    phase: str,
    dataset=None,
    error: Optional[str] = None,
) -> None:
    """
    Fire-and-forget Kafka publish to the generic notification.events topic.
    """
    if not job.user_id:
        return
    try:
        from kafka_utils.client import KafkaClient
        from kafka_utils.topics import Topics
    except Exception:
        return

    label = job.label or job.source_type
    type_prefix = f"devops_{job.source_type}"

    if phase == "started":
        title = "Collection started"
        message = f"Collecting {label} from {job.provider or 'provider'}…"
        link = f"{job.source_type}/jobs/{job.id}/progress"
    elif phase == "completed":
        title = "Collection completed"
        message = f"{label} ({job.collected_items} rows) is ready to analyse."
        link = (
            f"{job.source_type}/{dataset.id}/collect-metrics"
            if dataset is not None
            else f"{job.source_type}/jobs/{job.id}/progress"
        )
    else:  # failed
        title = "Collection failed"
        message = f"Collecting {label} failed: {error or 'unknown error'}"
        link = f"{job.source_type}/jobs/{job.id}/progress"

    payload = {
        "user_id": int(job.user_id),
        "workspace_id": int(job.workspace_id or 0),
        "repository_id": int(job.repository_id or 0),
        "type": f"{type_prefix}_{phase}",
        "title": title,
        "message": message,
        "link_url": link,
    }

    try:
        KafkaClient.publish(Topics.NOTIFICATION_EVENTS, payload)
    except Exception as exc:
        logger.warning("Failed to publish DevOps notification: %s", exc)
