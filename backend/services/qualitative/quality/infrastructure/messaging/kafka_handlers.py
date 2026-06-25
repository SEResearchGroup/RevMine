"""Kafka handlers for the qualitative service.

Reacts to `collection.events.completed`: when a collection was flagged for
qualitative analysis, auto-build the cleaned dataset so the dashboard is ready
before the user starts an analysis.
"""
from __future__ import annotations

import logging

from kafka_utils.client import KafkaClient
from kafka_utils.topics import Topics

logger = logging.getLogger(__name__)


def handle_collection_completed(payload: dict, topic: str) -> None:
    if not payload.get("for_qualitative"):
        return
    # Import here to avoid touching the ORM/app registry at import time.
    from quality.services.dataset_service import DatasetService

    try:
        dataset = DatasetService.ingest_from_event(payload)
        if dataset:
            logger.info(
                "[Qualitative] Auto-building dataset for collection %s",
                payload.get("collection_id"),
            )
    except Exception as exc:
        logger.error("[Qualitative] Failed to ingest collection event: %s", exc)


def start_kafka_consumers() -> None:
    KafkaClient.start_consumer(
        topics=[Topics.COLLECTION_COMPLETED],
        group_id="qualitative-service",
        handler=handle_collection_completed,
    )
