# Backward-compatibility shim — do not add logic here.
from analytics.infrastructure.messaging.kafka_handlers import (  # noqa: F401
    handle_collection_completed,
    start_kafka_consumers,
)
__all__ = ["handle_collection_completed", "start_kafka_consumers"]
