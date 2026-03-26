# collection_service/kafka_handlers.py
import logging
from kafka_utils.client import KafkaClient
from kafka_utils.topics import Topics

logger = logging.getLogger(__name__)


def start_kafka_consumers():
    # Collection n'a pas besoin de consumer particulier pour l'instant
    # (c'est Analysis qui consomme ses événements)
    logger.info("[Collection] Kafka ready (producer only for now)")