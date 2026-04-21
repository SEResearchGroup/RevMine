import json
import time
import uuid
import logging
from typing import Optional
from kafka import KafkaProducer, KafkaConsumer
from django.conf import settings
from .client import get_kafka_bootstrap

logger = logging.getLogger(__name__)


class RequestReplyClient:
    """
    Pattern request-reply sur Kafka.
    Le demandeur publie avec un correlation_id et écoute
    sur un topic de réponse dédié jusqu'à timeout.

    Usage :
        client = RequestReplyClient()
        result = client.call(
            request_topic=Topics.TOKENS_REQUEST,
            response_topic=Topics.TOKENS_RESPONSE,
            payload={"user_id": user_id, "workspace_id": ws_id},
            timeout=10,
        )
    """

    def __init__(self):
        self.producer = KafkaProducer(
            bootstrap_servers=get_kafka_bootstrap(),
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
        )

    def call(
        self,
        request_topic: str,
        response_topic: str,
        payload: dict,
        timeout: int = 10,
    ) -> Optional[dict]:
        correlation_id = str(uuid.uuid4())
        deadline = time.time() + timeout
        consumer = KafkaConsumer(
            response_topic,
            bootstrap_servers=get_kafka_bootstrap(),
            group_id=None,  # pas de group → lit depuis maintenant
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='latest',
            consumer_timeout_ms=1000,
        )

        try:
            # Ensure partition assignment is ready BEFORE publishing the
            # request — otherwise the reply may be produced and seeked past
            # while the consumer is still joining.
            while not consumer.assignment() and time.time() < deadline:
                consumer.poll(timeout_ms=100)

            request_payload = {**payload, 'correlation_id': correlation_id}
            self.producer.send(request_topic, value=request_payload)
            self.producer.flush()

            while time.time() < deadline:
                records = consumer.poll(timeout_ms=500)
                for messages in records.values():
                    for message in messages:
                        data = message.value
                        if data.get('correlation_id') == correlation_id:
                            return data

            logger.error(
                f"[Kafka] Request-reply timeout on {request_topic} (correlation_id={correlation_id})"
            )
            return None
        finally:
            consumer.close()
