import json
import threading
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

    Usage (côté Collection service) :
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
        event = threading.Event()
        listener_ready = threading.Event()
        result_holder = {}

        # Consumer éphémère qui écoute SA réponse uniquement
        def _listen():
            consumer = KafkaConsumer(
                response_topic,
                bootstrap_servers=get_kafka_bootstrap(),
                group_id=None,  # pas de group → lit depuis maintenant
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='latest',
                consumer_timeout_ms=timeout * 1000,
            )
            listener_ready.set()
            for message in consumer:
                data = message.value
                if data.get('correlation_id') == correlation_id:
                    result_holder['data'] = data
                    event.set()
                    break
            consumer.close()

        listener = threading.Thread(target=_listen, daemon=True)
        listener.start()
        listener_ready.wait(timeout=2)

        # Publie la requête avec le correlation_id
        request_payload = {**payload, 'correlation_id': correlation_id}
        self.producer.send(request_topic, value=request_payload)
        self.producer.flush()

        # Attend la réponse
        got_response = event.wait(timeout=timeout)
        if not got_response:
            logger.error(f"[Kafka] Request-reply timeout on {request_topic} (correlation_id={correlation_id})")
            return None

        return result_holder.get('data')