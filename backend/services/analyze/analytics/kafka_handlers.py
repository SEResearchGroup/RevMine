# analyze_service/kafka_handlers.py
import logging
from kafka_utils.client import KafkaClient
from kafka_utils.topics import Topics

logger = logging.getLogger(__name__)


def handle_collection_completed(payload: dict, topic: str):
    """
    Déclenche une analyse automatique dès qu'une collection se termine.
    Remplace le polling HTTP ou l'appel retour via gateway.
    """
    collection_id = payload.get('collection_id')
    user_id       = payload.get('user_id')
    workspace_id  = payload.get('workspace_id')

    if not collection_id or not user_id or not workspace_id:
        logger.warning("[Analysis] Invalid collection.completed payload: %s", payload)
        return

    logger.info(f"[Analysis] Collection completed event received: {collection_id}")

    try:
        KafkaClient.publish(
            Topics.ANALYSIS_REQUESTED,
            {
                'collection_id': collection_id,
                'user_id': user_id,
                'workspace_id': workspace_id,
                'status': 'queued',
            }
        )
    except Exception as e:
        logger.error(f"[Analysis] Failed to trigger analysis: {e}")


def start_kafka_consumers():
    KafkaClient.start_consumer(
        topics=[Topics.COLLECTION_COMPLETED],
        group_id='analyze-service',
        handler=handle_collection_completed,
    )
    logger.info("[Analysis] Kafka consumers started")