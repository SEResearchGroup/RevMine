import json
import requests
from django.http import JsonResponse, HttpResponse
from django.conf import settings
import logging
from rest_framework_simplejwt.tokens import AccessToken
import io


from .token_utils import extract_token_from_header, validate_token
from .service_clients import (
    ConfigurationServiceClient,
    CollectionServiceClient,
    ServiceClientError,
    build_collection_payload,
    build_branches_payload,
)

logger = logging.getLogger(__name__)


class ServiceProxyMiddleware:
    """
    Middleware that routes requests to the appropriate microservices
    after validating the JWT token.
    
    Responsibilities:
    - Route requests to appropriate services
    - Validate authentication
    - Orchestrate service calls for complex operations
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

        self.analyze_service_url = getattr(
            settings,
            'ANALYZE_SERVICE_URL',
            'http://analyze-service:8003/api/analysis'  
        )
        
        # Initialize service clients
        self.config_client = ConfigurationServiceClient(self.configuration_service_url)
        self.collection_client = CollectionServiceClient(self.collection_service_url)
        
        logger.info(f"ServiceProxyMiddleware initialized")
        logger.info(f"   Configuration Service: {self.configuration_service_url}")
        logger.info(f"   Collection Service: {self.collection_service_url}")
    
    def __call__(self, request):
        # Check if the route should be proxied
        if request.path.startswith('/api/workspaces'):
            return self.proxy_request(request, self.configuration_service_url, '/api/workspaces')
        
        if request.path.startswith('/api/collections'):
            return self.handle_collection_request(request)
        
        if request.path.startswith('/api/analysis'):
            return self.handle_analysis_request(request)
        
        return self.get_response(request)
    
    def handle_analysis_request(self, request):
        """
        Special handler for analysis requests.
        If /api/analysis/create is called without csv_file but with cleaned_data_id,
        fetch the CSV from collection service first.
        """
        # Extract user_id first
        print("Handling analysis request")
        auth_header = request.headers.get('Authorization', '')
        token = extract_token_from_header(auth_header)
        
        if not token:
            return JsonResponse(
                {'error': 'Authentication required'}, 
                status=401
            )
        
        token_data = validate_token(token)
        if not token_data:
            return JsonResponse(
                {'error': 'Invalid or expired token'}, 
                status=401
            )
        
        user_id = token_data['user_id']
        # Handle /api/analysis/create endpoint specially
        if (request.path == '/api/analysis/create/' or request.path == '/api/analysis/create' ) and request.method == 'POST':
            return self.handle_create_analysis(request, user_id)
        
        return self.proxy_request(request, self.analyze_service_url, '/api/analysis', user_id)
    
    def handle_create_analysis(self, request, user_id):
        """
        Handle analysis creation.
        If no csv_file is provided but cleaned_data_id is present,
        fetch the CSV from collection service first.
        """
        # Check if csv_file is in the request
        has_csv_file = 'csv_file' in request.FILES
        
        # Get cleaned_data_id and collection_id from POST data
        cleaned_data_id = request.POST.get('cleaned_data_id')
        collection_id = request.POST.get('collection_id')
        
        logger.info(f"Analysis create request - has_csv_file: {has_csv_file}, "
                   f"cleaned_data_id: {cleaned_data_id}, collection_id: {collection_id}")
        
        if not has_csv_file and cleaned_data_id:
            logger.info(f"No CSV file provided, fetching from collection service for cleaned_data_id: {cleaned_data_id}")
            print(f"No CSV file provided, fetching from collection service for cleaned_data_id: {cleaned_data_id}")
            
            # Determine file_type (default to 'structured', could be made configurable)
            file_type = request.POST.get('file_type', 'structured')
            
            try:
                # Fetch CSV from collection service
                csv_content, filename = self.fetch_csv_from_collection(
                    cleaned_data_id, file_type, user_id
                )
                
                if csv_content is None:
                    return JsonResponse(
                        {'error': 'Could not retrieve CSV from collection service'},
                        status=404
                    )
                
                logger.info(f"Successfully fetched CSV: {filename}")
                
                # Now proxy the request with the fetched CSV
                return self.proxy_analysis_with_csv(
                    request, user_id, csv_content, filename
                )
                
            except Exception as e:
                logger.error(f"Error fetching CSV from collection service: {e}")
                return JsonResponse(
                    {'error': 'Failed to fetch CSV from collection service', 'detail': str(e)},
                    status=500
                )
        
        # Otherwise, proxy the request normally
        return self.proxy_request(request, self.analyze_service_url, '/api/analysis', user_id)
    
    def fetch_csv_from_collection(self, cleaned_data_id, file_type, user_id):
        """
        Fetch CSV file from collection service.
        Returns (csv_bytes, filename) tuple or (None, None) if not found.
        """
        download_url = f"{self.collection_service_url}/cleaned-data/{cleaned_data_id}/download/{file_type}"
        
        logger.info(f"Fetching CSV from: {download_url}")
        
        headers = {
            'X-User-ID': str(user_id),
        }
        
        try:
            response = requests.get(
                download_url,
                headers=headers,
                timeout=30
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to fetch CSV: {response.status_code} - {response.text}")
                return None, None
            
            # Extract filename from Content-Disposition header
            content_disposition = response.headers.get('Content-Disposition', '')
            filename = 'cleaned_data.csv'  # default
            
            if content_disposition:
                # Parse filename from Content-Disposition
                # Format: attachment; filename="filename.csv"
                parts = content_disposition.split('filename=')
                if len(parts) > 1:
                    filename = parts[1].strip('"\'')
            
            return response.content, filename
            
        except requests.RequestException as e:
            logger.error(f"Request error fetching CSV: {e}")
            return None, None
    
    def proxy_analysis_with_csv(self, request, user_id, csv_content, filename):
        """
        Proxy analysis request with the fetched CSV file.
        """
        target_url = f"{self.analyze_service_url.rstrip('/')}/create/"
        
        logger.info(f"Proxying analysis request to {target_url} with fetched CSV: {filename}")
        
        headers = {
            'X-User-ID': str(user_id),
        }
        
        # Prepare form data
        data = []
        for key in request.POST.keys():
            # Skip file_type if it was only used for fetching
            if key == 'file_type':
                continue
            values = request.POST.getlist(key)
            for value in values:
                data.append((key, value))
        
        # Prepare files - include the fetched CSV
        files = {
            'csv_file': (filename, io.BytesIO(csv_content), 'text/csv')
        }
        
        # Include any other files from the original request
        for key, file in request.FILES.items():
            if key != 'csv_file':  # Don't override the fetched CSV
                files[key] = (file.name, file.read(), file.content_type)
        
        try:
            response = requests.post(
                url=target_url,
                headers=headers,
                data=data,
                files=files,
                timeout=60  # Longer timeout for analysis
            )
            
            logger.info(f"Response from analysis service: {response.status_code}")
            
            try:
                response_data = response.json()
            except ValueError:
                response_data = {'detail': response.text or 'Empty response'}
            
            return JsonResponse(response_data, status=response.status_code, safe=False)
            
        except requests.Timeout:
            logger.error(f"Timeout connecting to {target_url}")
            return JsonResponse(
                {'error': 'Service timeout', 'detail': 'The analysis service took too long to respond'},
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
    
    def handle_collection_request(self, request):
        """
        Special handler for collection requests.
        Validates authentication and routes to appropriate handler.
        """
        auth_header = request.headers.get('Authorization', '')
        token = extract_token_from_header(auth_header)
        
        if not token:
            return JsonResponse(
                {'error': 'Authentication required'}, 
                status=401
            )
        
        token_data = validate_token(token)
        if not token_data:
            return JsonResponse(
                {'error': 'Invalid or expired token'}, 
                status=401
            )
        
        user_id = token_data['user_id']
        
        # Handle collection start endpoint (needs workspace token)
        if request.path == '/api/collections/start' and request.method == 'POST':
            return self.handle_start_collection(request, user_id)
        
        # Handle branches endpoint (needs workspace token but doesn't create collection)
        if request.path == '/api/collections/branches/' and request.method == 'POST':
            return self.handle_get_branches(request, user_id)
        
        # For other collection endpoints, proxy directly
        return self.proxy_request(request, self.collection_service_url, '/api/collections', user_id)
    
    def handle_get_branches(self, request, user_id):
        """
        Handle fetching branches for a repository.
        Enriches the request with workspace token without creating a collection.
        """
        try:
            body_data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        
        repository_id = body_data.get('repository_id')
        workspace_id = body_data.get('workspace_id')
        
        if not repository_id or not workspace_id:
            return JsonResponse(
                {'error': 'repository_id and workspace_id are required'}, 
                status=400
            )
        
        logger.info(f"Fetching branches for repository {repository_id} in workspace {workspace_id}")
        
        try:
            # Get repository details and workspace token
            repository_details = self.config_client.get_repository(
                workspace_id, repository_id, user_id
            )
            workspace_token = self.config_client.get_workspace_token(workspace_id, user_id)
            
            # Build payload and call collection service
            branches_payload = build_branches_payload(repository_details, workspace_token)
            response_data, status_code = self.collection_client.get_branches(
                branches_payload, user_id
            )
            
            return JsonResponse(response_data, status=status_code)
            
        except ServiceClientError as e:
            error_response = {'error': e.message}
            if e.detail:
                error_response['detail'] = e.detail
            return JsonResponse(error_response, status=e.status_code)

    def handle_start_collection(self, request, user_id):
        """
        Handle starting a collection.
        Orchestrates fetching repository details, workspace token, and starting collection.
        """
        try:
            body_data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        
        repository_id = body_data.get('repository_id')
        workspace_id = body_data.get('workspace_id')
        
        if not repository_id or not workspace_id:
            return JsonResponse(
                {'error': 'repository_id and workspace_id are required'}, 
                status=400
            )
        
        logger.info(f"Starting collection for repository {repository_id} in workspace {workspace_id}")
        
        try:
            # Get repository details and workspace token
            repository_details = self.config_client.get_repository(
                workspace_id, repository_id, user_id
            )
            workspace_token = self.config_client.get_workspace_token(workspace_id, user_id)
            
            # Build payload and start collection
            collection_payload = build_collection_payload(
                repository_details, workspace_token, repository_id, workspace_id
            )
            response_data, status_code = self.collection_client.start_collection(
                collection_payload, user_id
            )
            
            return JsonResponse(response_data, status=status_code)
            
        except ServiceClientError as e:
            error_response = {'error': e.message}
            if e.detail:
                error_response['detail'] = e.detail
            return JsonResponse(error_response, status=e.status_code)
    
    def proxy_request(self, request, service_url, path_prefix, user_id=None):
        """Proxy the request to the microservice"""

        if user_id is None:
            auth_header = request.headers.get('Authorization', '')
            if not auth_header.startswith('Bearer '):
                return JsonResponse({'error': 'Authentication required'}, status=401)
            
            token = auth_header.split(' ')[1]
            try:
                access_token = AccessToken(token)
                user_id = access_token['user_id']
            except Exception as e:
                logger.error(f"Token validation failed: {e}")
                return JsonResponse({'error': 'Invalid or expired token'}, status=401)

        relative_path = request.path.replace(path_prefix, '', 1)
        target_url = f"{service_url.rstrip('/')}{relative_path}"
        if request.META.get('QUERY_STRING'):
            target_url = f"{target_url}?{request.META['QUERY_STRING']}"
        
        logger.info(f"Proxying {request.method} {request.path} → {target_url}")

        headers = {
            'X-User-ID': str(user_id),
        }

        body = None
        data = None
        files = None

        content_type = request.content_type or ''
        
        if request.method in ['POST', 'PUT', 'PATCH']:
            if content_type.startswith('application/json'):
                body = request.body
                headers['Content-Type'] = 'application/json'
            elif content_type.startswith('multipart/form-data'):
                data = []
                for key in request.POST.keys():
                    values = request.POST.getlist(key)
                    for value in values:
                        data.append((key, value))
                
                files = {}
                for key, file in request.FILES.items():
                    files[key] = (file.name, file.read(), file.content_type)
            else:
                body = request.body
                headers['Content-Type'] = content_type

        try:
            response = requests.request(
                method=request.method,
                url=target_url,
                headers=headers,
                data=data if data else body,
                files=files,
                timeout=30
            )
            logger.info(f"Response from service: {response.status_code}")
            
            # Check if this is a file download (CSV, etc.)
            content_type = response.headers.get('Content-Type', '')
            content_disposition = response.headers.get('Content-Disposition', '')
            
            # If it's a file download, return raw content without JSON wrapping
            if 'text/csv' in content_type or 'attachment' in content_disposition or '/download/' in target_url:
                logger.info(f"Proxying file download: {content_type}")
                http_response = HttpResponse(
                    response.content,
                    status=response.status_code,
                    content_type=content_type
                )
                # Copy Content-Disposition header for proper filename
                if content_disposition:
                    http_response['Content-Disposition'] = content_disposition
                return http_response
            
            # Return the response as JSON
            try:
                response_data = response.json()
            except ValueError:
                response_data = {'detail': response.text or 'Empty response'}

            return JsonResponse(response_data, status=response.status_code, safe=False)

        except requests.Timeout:
            logger.error(f"Timeout connecting to {target_url}")
            return JsonResponse({'error': 'Service timeout', 'detail': 'The service took too long to respond'}, status=504)
        except requests.ConnectionError as e:
            logger.error(f"Connection error to {target_url}: {e}")
            return JsonResponse({'error': 'Service unavailable', 'detail': str(e)}, status=503)
        except requests.RequestException as e:
            logger.error(f"Request error to {target_url}: {e}")
            return JsonResponse({'error': 'Service error', 'detail': str(e)}, status=503)