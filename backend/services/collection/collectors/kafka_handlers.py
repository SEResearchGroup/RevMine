"""Backward-compatibility shim.

Canonical location: ``collectors.infrastructure.messaging.kafka_handlers``.
"""
from collectors.infrastructure.messaging.kafka_handlers import (  # noqa: F401
    start_kafka_consumers,
)

__all__ = ["start_kafka_consumers"]
