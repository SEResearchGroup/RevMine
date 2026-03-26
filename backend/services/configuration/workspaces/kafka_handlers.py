# configuration_service/kafka_handlers.py
import logging
from kafka_utils.client import KafkaClient
from kafka_utils.topics import Topics
from .models import Workspace

logger = logging.getLogger(__name__)


def handle_token_request(payload: dict, topic: str):
    """
    Reçoit une demande de token depuis Collection ou Analysis.
    Répond sur Topics.TOKENS_RESPONSE avec les credentials.
    """
    user_id       = payload.get('user_id')
    workspace_id  = payload.get('workspace_id')
    correlation_id = payload.get('correlation_id')

    if not user_id or not workspace_id:
        KafkaClient.publish(
            Topics.TOKENS_RESPONSE,
            {
                'correlation_id': correlation_id,
                'status': 'error',
                'error': 'user_id and workspace_id are required',
            },
        )
        return

    logger.info(f"[Config] Token request received for user={user_id} workspace={workspace_id}")

    try:
        workspace = Workspace.objects.get(
            id=workspace_id,
            user=user_id,
        )
        response = {
            'correlation_id': correlation_id,
            'user_id': user_id,
            'workspace_id': workspace_id,
            'token': workspace.get_token(),
            'platform': workspace.platform,
            'url': workspace.url,
            'status': 'ok',
        }
    except Workspace.DoesNotExist:
        response = {
            'correlation_id': correlation_id,
            'user_id': user_id,
            'workspace_id': workspace_id,
            'status': 'error',
            'error': 'Workspace not found',
        }

    KafkaClient.publish(Topics.TOKENS_RESPONSE, response)
    logger.info(
        "[Config] Token response published for user=%s workspace=%s status=%s",
        user_id,
        workspace_id,
        response.get('status'),
    )


def start_kafka_consumers():
    KafkaClient.start_consumer(
        topics=[Topics.TOKENS_REQUEST],
        group_id='configuration-service',
        handler=handle_token_request,
    )
    logger.info("[Config] Kafka consumers started")