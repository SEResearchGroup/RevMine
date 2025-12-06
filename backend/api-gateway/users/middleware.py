
import requests
from django.http import JsonResponse
from django.conf import settings
from rest_framework_simplejwt.tokens import AccessToken
import logging

logger = logging.getLogger(__name__)


class ServiceProxyMiddleware:
    """
    Middleware that routes requests to the appropriate microservices
    after validating the JWT token.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        self.configuration_service_url = getattr(
            settings, 
            'CONFIGURATION_SERVICE_URL', 
            'http://configuration-service:8001/api/workspaces'
        )
        
        self.collection_service_url = getattr(
            settings,
            'COLLECTION_SERVICE_URL',
            'http://collection-service:8002/api/collections'  
        )
        
        logger.info(f"🔧 ServiceProxyMiddleware initialized")
        logger.info(f"   Configuration Service: {self.configuration_service_url}")
        logger.info(f"   Collection Service: {self.collection_service_url}")
    
    def __call__(self, request):
        # Check if the route should be proxied
        if request.path.startswith('/api/workspaces'):
            return self.proxy_request(request, self.configuration_service_url, '/api/workspaces')
        
        if request.path.startswith('/api/collections'):
            return self.handle_collection_request(request)
        
        return self.get_response(request)
    
    def handle_collection_request(self, request):
        """
        Special handler for collection requests
        Fetches repository details from configuration service first
        """
        # Extract JWT token
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return JsonResponse(
                {'error': 'Authentication required'}, 
                status=401
            )
        
        token = auth_header.split(' ')[1]
        
        try:
            access_token = AccessToken(token)
            user_id = access_token['user_id']
        except Exception as e:
            logger.error(f"Token validation failed: {e}")
            return JsonResponse(
                {'error': 'Invalid or expired token'}, 
                status=401
            )
        
        # Handle collection start endpoint
        if request.path == '/api/collections/start' and request.method == 'POST':
            return self.handle_start_collection(request, user_id)
        
        # For other collection endpoints, proxy directly
        return self.proxy_request(request, self.collection_service_url, '/api/collections', user_id)
    
    def handle_start_collection(self, request, user_id):
        """
        Handle collection start request:
        1. Get repository details from configuration service
        2. Forward to collection service with repository details
        """
        import json
        
        try:
            body_data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse(
                {'error': 'Invalid JSON'}, 
                status=400
            )
        
        repository_id = body_data.get('repository_id')
        workspace_id = body_data.get('workspace_id')
        
        if not repository_id or not workspace_id:
            return JsonResponse(
                {'error': 'repository_id and workspace_id are required'}, 
                status=400
            )
        
        logger.info(f"🔄 Starting collection for repository {repository_id} in workspace {workspace_id}")
        
        # Step 1: Get repository details from configuration service
        config_url = f"{self.configuration_service_url.rstrip('/')}/{workspace_id}/repositories/{repository_id}/"
        
        logger.info(f"📡 Fetching repository details from: {config_url}")
        
        try:
            config_response = requests.get(
                config_url,
                headers={'X-User-ID': str(user_id)},
                timeout=10
            )
            
            if config_response.status_code != 200:
                logger.error(f" Configuration service error: {config_response.status_code}")
                return JsonResponse(
                    {
                        'error': 'Failed to fetch repository details',
                        'status': config_response.status_code
                    },
                    status=config_response.status_code
                )
            
            repository_details = config_response.json()
            logger.info(f" Repository details fetched: {repository_details.get('full_name')}")
            
        except requests.RequestException as e:
            logger.error(f" Error fetching repository: {e}")
            return JsonResponse(
                {'error': 'Configuration service unavailable', 'detail': str(e)},
                status=503
            )
        
        # Step 2: Forward to collection service with repository details
        collection_payload = {
            'repository_id': repository_id,
            'workspace_id': workspace_id,
            'repository_name': repository_details.get('name'),
            'repository_full_name': repository_details.get('full_name'),
            'platform': repository_details.get('platform'),
            'repository_url': repository_details.get('web_url'),
            'default_branch': repository_details.get('default_branch'),
        }
        
        collection_url = f"{self.collection_service_url}/start/"
        logger.info(f"📡 Forwarding to collection service: {collection_url}")
        
        try:
            collection_response = requests.post(
                collection_url,
                headers={
                    'X-User-ID': str(user_id),
                    'Content-Type': 'application/json'
                },
                json=collection_payload,
                timeout=30
            )
            
            logger.info(f" Collection service responded: {collection_response.status_code}")
            
            return JsonResponse(
                collection_response.json(),
                status=collection_response.status_code
            )
            
        except requests.RequestException as e:
            logger.error(f" Collection service error: {e}")
            return JsonResponse(
                {'error': 'Collection service unavailable', 'detail': str(e)},
                status=503
            )
    
    def proxy_request(self, request, service_url, path_prefix, user_id=None):
        """Proxy the request to the microservice"""
        
        # Extract the JWT token if not already provided
        if user_id is None:
            auth_header = request.headers.get('Authorization', '')
            if not auth_header.startswith('Bearer '):
                return JsonResponse(
                    {'error': 'Authentication required'}, 
                    status=401
                )
            
            token = auth_header.split(' ')[1]
            
            try:
                access_token = AccessToken(token)
                user_id = access_token['user_id']
            except Exception as e:
                logger.error(f"Token validation failed: {e}")
                return JsonResponse(
                    {'error': 'Invalid or expired token'}, 
                    status=401
                )
        
        # Build the target URL
        relative_path = request.path.replace(path_prefix, '', 1)
        target_url = f"{service_url.rstrip('/')}{relative_path}"
        
        if request.META.get('QUERY_STRING'):
            target_url = f"{target_url}?{request.META['QUERY_STRING']}"
        
        logger.info(f" Proxying {request.method} {request.path} → {target_url}")
        
        # Prepare headers
        headers = {
            'X-User-ID': str(user_id),
            'Content-Type': request.content_type or 'application/json',
        }
        
        body = None
        if request.method in ['POST', 'PUT', 'PATCH']:
            try:
                body = request.body
            except Exception as e:
                logger.error(f"Error reading request body: {e}")
        
        try:
            response = requests.request(
                method=request.method,
                url=target_url,
                headers=headers,
                data=body,
                timeout=30
            )
            
            logger.info(f" Response from service: {response.status_code}")
            
            # Return the response
            try:
                response_data = response.json()
            except ValueError:
                response_data = {'detail': response.text or 'Empty response'}
            
            return JsonResponse(
                response_data,
                status=response.status_code,
                safe=False
            )
        
        except requests.Timeout:
            logger.error(f" Timeout connecting to {target_url}")
            return JsonResponse(
                {'error': 'Service timeout', 'detail': 'The service took too long to respond'}, 
                status=504
            )
        except requests.ConnectionError as e:
            logger.error(f" Connection error to {target_url}: {e}")
            return JsonResponse(
                {'error': 'Service unavailable', 'detail': str(e)}, 
                status=503
            )
        except requests.RequestException as e:
            logger.error(f" Request error to {target_url}: {e}")
            return JsonResponse(
                {'error': 'Service error', 'detail': str(e)}, 
                status=503
            )