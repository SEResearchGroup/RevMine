"""Backward-compatibility shim.

Canonical location: ``collectors.infrastructure.messaging.kafka_handlers``
"""
from collectors.infrastructure.messaging.kafka_handlers import start_kafka_consumers  # noqa: F401

__all__ = ["start_kafka_consumers"]



def start_kafka_consumers():
    # Collection n'a pas besoin de consumer particulier pour l'instant
    # (c'est Analysis qui consomme ses événements)
    logger.info("[Collection] Kafka ready (producer only for now)")