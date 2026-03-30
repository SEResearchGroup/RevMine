import logging
import requests
from django.http import JsonResponse, HttpResponse

from ..auth.token_utils import extract_user_from_request
from ..utils.request_utils import prepare_request_data
from .file_proxy import detect_file_response, create_file_response

logger = logging.getLogger(__name__)


class BaseProxyHandler:
    """Generic proxy handler for all services"""
    
    def __init__(self, service_url, path_prefix):
        """
        Args:
            service_url: Base URL of the service
            path_prefix: Path prefix to remove (e.g., '/api/workspaces')
        """
        self.service_url = service_url
        self.path_prefix = path_prefix
    
    def build_target_url(self, request):
        """Build the target URL from the request"""
        relative_path = request.path.replace(self.path_prefix, '', 1)
        target_url = f"{self.service_url.rstrip('/')}{relative_path}"
        
        if request.META.get('QUERY_STRING'):
            target_url = f"{target_url}?{request.META['QUERY_STRING']}"
        
        return target_url
    
    def proxy_request(self, request, user_id=None):
        """
        Proxy a request to the microservice.
        
        Args:
            request: Django request
            user_id: User ID (optional, will be extracted if absent)
        
        Returns:
            JsonResponse or HttpResponse
        """
        # Extract user_id if not provided
        if user_id is None:
            user_id, error_response = extract_user_from_request(request)
            if error_response:
                return error_response
        
        # Build the target URL
        target_url = self.build_target_url(request)
        logger.info(f"Proxying {request.method} {request.path} → {target_url}")
        
        # Prepare headers
        headers = {'X-User-ID': str(user_id)}
        
        # Prepare data
        body, data, files, content_type = prepare_request_data(request)
        if content_type:
            headers['Content-Type'] = content_type
        
        # Execute the request
        try:
            # Use a longer timeout for file uploads and heavy processing
            is_upload = bool(files)
            req_timeout = 1800 if is_upload else 300  # 30 min for uploads, 5 min otherwise

            response = requests.request(
                method=request.method,
                url=target_url,
                headers=headers,
                data=data if data else body,
                files=files,
                timeout=req_timeout,
            )
            
            logger.info(f"Response from service: {response.status_code}")
            
            # Handle file responses
            if detect_file_response(response, target_url):
                return create_file_response(response)
            
            # Standard JSON response
            return self._create_json_response(response)
            
        except requests.Timeout:
            logger.error(f"Timeout connecting to {target_url}")
            return JsonResponse(
                {'error': 'Service timeout', 'detail': 'The service took too long to respond'}, 
                status=504
            )
        except requests.ConnectionError as e:
            logger.error(f"Connection error to {target_url}: {e}")
            return JsonResponse(
                {'error': 'Service unavailable', 'detail': str(e)}, 
                status=503
            )
        except requests.RequestException as e:
            logger.error(f"Request error to {target_url}: {e}")
            return JsonResponse(
                {'error': 'Service error', 'detail': str(e)}, 
                status=503
            )
    
    def _create_json_response(self, response):
        """Create a JsonResponse from the service response"""
        try:
            response_data = response.json()
        except ValueError:
            response_data = {'detail': response.text or 'Empty response'}
        
        return JsonResponse(response_data, status=response.status_code, safe=False)