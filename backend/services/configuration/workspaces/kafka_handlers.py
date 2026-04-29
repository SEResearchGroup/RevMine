# SHIM: content moved to workspaces.infrastructure.messaging.kafka_handlers
# re-exported for backward compatibility.
from workspaces.infrastructure.messaging.kafka_handlers import (
    handle_token_request,
    start_kafka_consumers,
)

__all__ = ["handle_token_request", "start_kafka_consumers"]
