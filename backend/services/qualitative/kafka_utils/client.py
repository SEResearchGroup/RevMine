import json
import logging
import threading
import time
from typing import Callable, Optional
from kafka import KafkaProducer, KafkaConsumer
from django.conf import settings

logger = logging.getLogger(__name__)


def get_kafka_bootstrap():
    return getattr(settings, 'KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')


class KafkaClient:
    """Reusable producer + consumer. Instantiate once at service startup."""

    _producer: Optional[KafkaProducer] = None

    @classmethod
    def get_producer(cls) -> KafkaProducer:
        if cls._producer is None:
            cls._producer = KafkaProducer(
                bootstrap_servers=get_kafka_bootstrap(),
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                acks='all',
                retries=3,
            )
        return cls._producer

    @classmethod
    def publish(cls, topic: str, payload: dict, key: str = None):
        """Publish a message to a topic."""
        try:
            producer = cls.get_producer()
            future = producer.send(topic, value=payload, key=key)
            future.get(timeout=10)  # wait for broker ack
            logger.debug(f"[Kafka] Published to {topic}: {payload}")
        except Exception as e:
            logger.error(f"[Kafka] Publish error on {topic}: {e}")
            raise

    @classmethod
    def start_consumer(
        cls,
        topics: list[str],
        group_id: str,
        handler: Callable[[dict, str], None],
        daemon: bool = True,
    ) -> threading.Thread:
        """Start a consumer in a background thread.

        handler(payload: dict, topic: str) is called for each message.
        """
        def _consume():
            while True:
                try:
                    consumer = KafkaConsumer(
                        *topics,
                        bootstrap_servers=get_kafka_bootstrap(),
                        group_id=group_id,
                        value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                        auto_offset_reset='earliest',
                        enable_auto_commit=True,
                    )
                    logger.info(f"[Kafka] Consumer started: topics={topics} group={group_id}")
                    for message in consumer:
                        try:
                            handler(message.value, message.topic)
                        except Exception as e:
                            logger.error(f"[Kafka] Handler error on {message.topic}: {e}")
                except Exception as e:
                    logger.error(f"[Kafka] Consumer crashed for group={group_id}: {e}")
                    time.sleep(3)

        thread = threading.Thread(target=_consume, daemon=daemon, name=f"kafka-{group_id}")
        thread.start()
        return thread
