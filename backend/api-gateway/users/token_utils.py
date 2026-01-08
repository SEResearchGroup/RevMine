"""
Token validation utilities.
Handles JWT token extraction and validation.
"""
from rest_framework_simplejwt.tokens import AccessToken
import logging

logger = logging.getLogger(__name__)


def extract_token_from_header(auth_header: str) -> str | None:
    """
    Extract the JWT token from the Authorization header.
    
    Args:
        auth_header: The Authorization header value (e.g., "Bearer <token>")
        
    Returns:
        The token string if valid, None otherwise
    """
    if not auth_header or not auth_header.startswith('Bearer '):
        return None
    return auth_header.split(' ')[1]


def validate_token(token: str) -> dict | None:
    """
    Validate a JWT token and extract its payload.
    
    Args:
        token: The JWT token string
        
    Returns:
        Dictionary with token payload including 'user_id', or None if invalid
    """
    try:
        access_token = AccessToken(token)
        return {
            'user_id': access_token['user_id'],
            'token_obj': access_token
        }
    except Exception as e:
        logger.error(f"Token validation failed: {e}")
        return None


def get_user_id_from_request(request) -> int | None:
    """
    Extract and validate user_id from request's Authorization header.
    
    Args:
        request: Django HTTP request object
        
    Returns:
        user_id if token is valid, None otherwise
    """
    auth_header = request.headers.get('Authorization', '')
    token = extract_token_from_header(auth_header)
    
    if not token:
        return None
    
    token_data = validate_token(token)
    return token_data['user_id'] if token_data else None
