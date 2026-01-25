"""
Service client utilities.
Handles communication with microservices (configuration, collection).
"""
import requests
import logging
from typing import Any

logger = logging.getLogger(__name__)


class ServiceClientError(Exception):
    """Base exception for service client errors."""
    def __init__(self, message: str, status_code: int = 500, detail: str = None):
        self.message = message
        self.status_code = status_code
        self.detail = detail
        super().__init__(message)


class ConfigurationServiceClient:
    """Client for communicating with the Configuration Service."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
    
    def get_repository(self, workspace_id: str, repository_id: str, user_id: int) -> dict:
        """
        Fetch repository details from the configuration service.
        
        Args:
            workspace_id: The workspace ID
            repository_id: The repository ID
            user_id: The authenticated user's ID
            
        Returns:
            Repository details dictionary
            
        Raises:
            ServiceClientError: If the request fails
        """
        url = f"{self.base_url}/{workspace_id}/repositories/{repository_id}/"
        logger.info(f"Fetching repository details from: {url}")
        
        try:
            response = requests.get(
                url,
                headers={'X-User-ID': str(user_id)},
                timeout=10
            )
            
            if response.status_code != 200:
                logger.error(f"Configuration service error: {response.status_code}")
                raise ServiceClientError(
                    message='Failed to fetch repository details',
                    status_code=response.status_code
                )
            
            repository_details = response.json()
            logger.info(f"Repository details fetched: {repository_details.get('full_name')}")
            return repository_details
            
        except requests.RequestException as e:
            logger.error(f"Error fetching repository: {e}")
            raise ServiceClientError(
                message='Configuration service unavailable',
                status_code=503,
                detail=str(e)
            )
    
    def get_workspace_token(self, workspace_id: str, user_id: int) -> str:
        """
        Fetch the workspace token from the configuration service.
        
        Args:
            workspace_id: The workspace ID
            user_id: The authenticated user's ID
            
        Returns:
            The workspace token string
            
        Raises:
            ServiceClientError: If the request fails or token not found
        """
        url = f"{self.base_url}/{workspace_id}/token/"
        logger.info(f"Fetching workspace token from: {url}")
        
        try:
            response = requests.get(
                url,
                headers={'X-User-ID': str(user_id)},
                timeout=10
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to fetch workspace token: {response.status_code}")
                raise ServiceClientError(
                    message='Failed to fetch workspace token',
                    status_code=response.status_code
                )
            
            workspace_data = response.json()
            workspace_token = workspace_data.get('token')
            
            if not workspace_token:
                logger.error("No token found in workspace response")
                raise ServiceClientError(
                    message='Workspace token not found',
                    status_code=500
                )
            
            logger.info("Workspace token retrieved")
            return workspace_token
            
        except requests.RequestException as e:
            logger.error(f"Error fetching workspace token: {e}")
            raise ServiceClientError(
                message='Configuration service unavailable',
                status_code=503,
                detail=str(e)
            )


class CollectionServiceClient:
    """Client for communicating with the Collection Service."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
    
    def start_collection(self, payload: dict, user_id: int) -> tuple[dict, int]:
        """
        Start a collection process.
        
        Args:
            payload: Collection payload with repository details and token
            user_id: The authenticated user's ID
            
        Returns:
            Tuple of (response_data, status_code)
            
        Raises:
            ServiceClientError: If the request fails
        """
        url = f"{self.base_url}/start/"
        logger.info(f"Forwarding to collection service: {url}")
        
        try:
            response = requests.post(
                url,
                headers={
                    'X-User-ID': str(user_id),
                    'Content-Type': 'application/json'
                },
                json=payload,
                timeout=30
            )
            
            logger.info(f"Collection service responded: {response.status_code}")
            return response.json(), response.status_code
            
        except requests.RequestException as e:
            logger.error(f"Collection service error: {e}")
            raise ServiceClientError(
                message='Collection service unavailable',
                status_code=503,
                detail=str(e)
            )
    
    def get_branches(self, payload: dict, user_id: int) -> tuple[dict, int]:
        """
        Fetch branches for a repository.
        
        Args:
            payload: Branches payload with platform, token, and repository info
            user_id: The authenticated user's ID
            
        Returns:
            Tuple of (response_data, status_code)
            
        Raises:
            ServiceClientError: If the request fails
        """
        url = f"{self.base_url}/branches/"
        
        try:
            response = requests.post(
                url,
                headers={
                    'X-User-ID': str(user_id),
                    'Content-Type': 'application/json'
                },
                json=payload,
                timeout=30
            )
            
            return response.json(), response.status_code
            
        except requests.RequestException as e:
            logger.error(f"Collection service error: {e}")
            raise ServiceClientError(
                message='Collection service unavailable',
                status_code=503,
                detail=str(e)
            )


def build_collection_payload(repository_details: dict, workspace_token: str, 
                             repository_id: str, workspace_id: str) -> dict:
    """
    Build the payload for starting a collection.
    
    Args:
        repository_details: Repository details from configuration service
        workspace_token: The workspace token
        repository_id: The repository ID
        workspace_id: The workspace ID
        
    Returns:
        Collection payload dictionary
    """
    return {
        'repository_id': repository_id,
        'workspace_id': workspace_id,
        'repository_name': repository_details.get('name'),
        'repository_full_name': repository_details.get('full_name'),
        'platform': repository_details.get('platform'),
        'repository_url': repository_details.get('web_url'),
        'default_branch': repository_details.get('default_branch'),
        'external_id': repository_details.get('external_id'),
        'token': workspace_token,
    }


def build_branches_payload(repository_details: dict, workspace_token: str) -> dict:
    """
    Build the payload for fetching branches.
    
    Args:
        repository_details: Repository details from configuration service
        workspace_token: The workspace token
        
    Returns:
        Branches payload dictionary
    """
    return {
        'platform': repository_details.get('platform'),
        'token': workspace_token,
        'repository_full_name': repository_details.get('full_name'),
        'default_branch': repository_details.get('default_branch'),
    }
