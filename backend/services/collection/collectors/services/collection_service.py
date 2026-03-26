# collection_service/services/collection_service.py
import logging
from kafka_utils.client import KafkaClient
from kafka_utils.request_reply import RequestReplyClient
from kafka_utils.topics import Topics

logger = logging.getLogger(__name__)

_rr_client = RequestReplyClient()  # instance unique


def fetch_tokens_for_workspace(user_id: str, workspace_id: str) -> dict:
    """
    Remplace l'appel HTTP vers Configuration via Gateway.
    Maintenant → request-reply Kafka direct.
    """
    response = _rr_client.call(
        request_topic=Topics.TOKENS_REQUEST,
        response_topic=Topics.TOKENS_RESPONSE,
        payload={
            'user_id': user_id,
            'workspace_id': workspace_id,
        },
        timeout=10,
    )

    if not response or response.get('status') != 'ok':
        raise ValueError(f"Could not retrieve tokens: {response}")

    return {
        'token': response['token'],
        'platform': response.get('platform'),
        'url': response.get('url'),
    }


def notify_collection_started(collection_id: str, user_id: str, workspace_id: str):
    KafkaClient.publish(
        Topics.COLLECTION_STARTED,
        {
            'collection_id': collection_id,
            'user_id': user_id,
            'workspace_id': workspace_id,
        }
    )


def notify_collection_completed(collection_id: str, result_summary: dict):
    KafkaClient.publish(
        Topics.COLLECTION_COMPLETED,
        {
            'collection_id': collection_id,
            **result_summary,
        }
    )