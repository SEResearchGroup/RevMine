"""
Infrastructure – Messaging Layer
==================================
Kafka handlers for the analyze service. Reacts to events published by
other services (e.g. collection.completed) and triggers analysis workflows.
No business logic lives here – just message routing.
"""
from __future__ import annotations

import logging

from kafka_utils.client import KafkaClient
from kafka_utils.topics import Topics

logger = logging.getLogger(__name__)


def handle_collection_completed(payload: dict, topic: str) -> None:
    """
    Trigger automatic analysis when a collection completes.
    Publishes an analysis.requested event so the workflow continues
    asynchronously without coupling the analysis service to HTTP callbacks.
    """
    collection_id = payload.get("collection_id")
    user_id = payload.get("user_id")
    workspace_id = payload.get("workspace_id")

    if not collection_id or not user_id or not workspace_id:
        logger.warning("[Analysis] Invalid collection.completed payload: %s", payload)
        return

    logger.info("[Analysis] Collection completed event received: %s", collection_id)

    try:
        KafkaClient.publish(
            Topics.ANALYSIS_REQUESTED,
            {
                "collection_id": collection_id,
                "user_id": user_id,
                "workspace_id": workspace_id,
                "status": "queued",
            },
        )
    except Exception as exc:
        logger.error("[Analysis] Failed to trigger analysis: %s", exc)


def start_kafka_consumers() -> None:
    """Start all Kafka consumers for the analyze service."""
    KafkaClient.start_consumer(
        topics=[Topics.COLLECTION_COMPLETED],
        group_id="analyze-service",
        handler=handle_collection_completed,
    )
