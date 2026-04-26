"""
Kafka request-reply helper to fetch a workspace's stored provider token from
the configuration service. Mirrors the pattern used in the collection service
(see collectors/services.py::resolve_workspace_token) so DevOps live-collection
endpoints can reuse the user's already-connected GitHub/GitLab workspaces
instead of asking them to paste a token.
"""

from __future__ import annotations

import logging
from typing import Optional

from kafka_utils.request_reply import RequestReplyClient
from kafka_utils.topics import Topics

logger = logging.getLogger(__name__)


_rr_client: Optional[RequestReplyClient] = None


def _get_rr_client() -> RequestReplyClient:
    global _rr_client
    if _rr_client is None:
        _rr_client = RequestReplyClient()
    return _rr_client


class WorkspaceTokenError(Exception):
    """Raised when the configuration service does not return a usable token."""


def resolve_workspace_token(user_id: int, workspace_id: int) -> dict:
    """
    Ask the configuration service for a workspace's decrypted token.
    Returns {'token': str, 'platform': str} on success.
    """
    response = _get_rr_client().call(
        request_topic=Topics.TOKENS_REQUEST,
        response_topic=Topics.TOKENS_RESPONSE,
        payload={
            'user_id': user_id,
            'workspace_id': workspace_id,
        },
        timeout=10,
    )

    if not response or response.get('status') != 'ok':
        raise WorkspaceTokenError(
            f'Configuration service returned no token: {response}'
        )

    token = response.get('token')
    if not token:
        raise WorkspaceTokenError('Token missing in configuration response')

    return {
        'token': token,
        'platform': response.get('platform'),
    }
