"""Messaging layer — Kafka event producers and consumers."""
from collectors.infrastructure.messaging.kafka_handlers import start_kafka_consumers

__all__ = ["start_kafka_consumers"]
