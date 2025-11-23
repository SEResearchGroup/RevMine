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
        
        logger.info(f"🔧 ServiceProxyMiddleware initialized with URL: {self.configuration_service_url}")
    
    def __call__(self, request):
        # Check if the route should be proxied
        if request.path.startswith('/api/workspaces'):
            return self.proxy_request(request)
        
        return self.get_response(request)
    
    def proxy_request(self, request):
        """Proxy the request to the microservice"""
        
        # Extract the JWT token
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
        
        relative_path = request.path.replace('/api/workspaces', '', 1)
        
        target_url = f"{self.configuration_service_url.rstrip('/')}{relative_path}"
        
        if request.META.get('QUERY_STRING'):
            target_url = f"{target_url}?{request.META['QUERY_STRING']}"
        
        logger.info(f"🔄 Proxying {request.method} {request.path} → {target_url}")
        
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
            
            logger.info(f"✅ Response from service: {response.status_code}")
            
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
            logger.error(f"❌ Timeout connecting to {target_url}")
            return JsonResponse(
                {'error': 'Service timeout', 'detail': 'The service took too long to respond'}, 
                status=504
            )
        except requests.ConnectionError as e:
            logger.error(f"❌ Connection error to {target_url}: {e}")
            return JsonResponse(
                {'error': 'Service unavailable', 'detail': str(e)}, 
                status=503
            )
        except requests.RequestException as e:
            logger.error(f"❌ Request error to {target_url}: {e}")
            return JsonResponse(
                {'error': 'Service error', 'detail': str(e)}, 
                status=503
            )