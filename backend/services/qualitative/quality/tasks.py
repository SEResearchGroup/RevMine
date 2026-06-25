"""Background dataset build (ETL). Mirrors the collection service's
thread-based worker pattern — no Celery dependency for Phase A."""
from __future__ import annotations

import logging
import re
import threading

from django.utils import timezone

from quality.models import QualitativeDataset
from quality.infrastructure.storage.minio_client import MinIOClient
from quality.infrastructure.etl.builder import build_dataset
from kafka_utils.client import KafkaClient
from kafka_utils.topics import Topics

logger = logging.getLogger(__name__)


def run_build_in_background(dataset_id: str) -> None:
    thread = threading.Thread(target=build_dataset_task, args=(dataset_id,), daemon=True)
    thread.start()
    logger.info("Qualitative build thread started", extra={"dataset_id": dataset_id})


def build_dataset_task(dataset_id: str) -> None:
    try:
        dataset = QualitativeDataset.objects.get(id=dataset_id)
    except QualitativeDataset.DoesNotExist:
        logger.warning("Qualitative dataset not found", extra={"dataset_id": dataset_id})
        return

    dataset.status = "building"
    dataset.error_message = None
    dataset.save(update_fields=["status", "error_message", "updated_at"])

    try:
        data = MinIOClient().get_json(dataset.qualitative_data_filename)
        if not data:
            raise ValueError(
                f"Qualitative file not found in storage: {dataset.qualitative_data_filename}"
            )

        # Resilience for older collection events that predate the platform/repo
        # fields on collection.events.completed: infer them from the data/filename.
        if not dataset.platform:
            if "pull_requests" in data:
                dataset.platform = "github"
            elif "merge_requests" in data:
                dataset.platform = "gitlab"
        if not dataset.repository_full_name:
            m = re.match(r"(.+?)_collection\d+_", dataset.qualitative_data_filename or "")
            if m:
                dataset.repository_full_name = m.group(1)

        stats = build_dataset(dataset, data)
        dataset.stats = stats
        dataset.status = "ready"
        dataset.built_at = timezone.now()
        dataset.save()

        logger.info(
            "Qualitative dataset built",
            extra={
                "dataset_id": dataset_id,
                "repository": dataset.repository_full_name,
                "comments_human": stats.get("comments_human"),
                "event": "qualitative_dataset_ready",
            },
        )

        try:
            KafkaClient.publish(
                Topics.QUALITATIVE_COMPLETED,
                {
                    "dataset_id": str(dataset.id),
                    "collection_id": dataset.collection_id,
                    "user_id": dataset.user_id,
                    "workspace_id": dataset.workspace_id,
                    "status": "ready",
                },
            )
        except Exception as pub_err:
            logger.warning("Could not publish QUALITATIVE_COMPLETED: %s", pub_err)

    except Exception as exc:
        logger.error(
            "Qualitative dataset build failed",
            extra={"dataset_id": dataset_id, "error": str(exc), "event": "qualitative_build_failed"},
            exc_info=True,
        )
        try:
            dataset.status = "failed"
            dataset.error_message = str(exc)
            dataset.save(update_fields=["status", "error_message", "updated_at"])
        except Exception:
            pass
