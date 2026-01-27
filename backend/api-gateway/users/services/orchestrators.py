import io
import logging
import requests
from django.http import JsonResponse

from ..utils.request_utils import parse_json_body, prepare_multipart_data
from .service_clients import (
    ServiceClientError,
    build_collection_payload,
    build_branches_payload
)

logger = logging.getLogger(__name__)


class CollectionOrchestrator:
    
    def __init__(self, config_client, collection_client):
        self.config_client = config_client
        self.collection_client = collection_client
    
    def start_collection(self, request, user_id):
        """
        Starts a collection.
        Requires: repository details + workspace token
        """
        # Parse JSON body
        body_data, error_response = parse_json_body(request)
        if error_response:
            return error_response
        
        repository_id = body_data.get('repository_id')
        workspace_id = body_data.get('workspace_id')
        
        if not repository_id or not workspace_id:
            return JsonResponse(
                {'error': 'repository_id and workspace_id are required'}, 
                status=400
            )
        
        logger.info(f"Starting collection for repository {repository_id} in workspace {workspace_id}")
        
        try:
            # Fetch required details
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
    
    def get_branches(self, request, user_id):
        """
        Fetches branches of a repository.
        Requires: repository details + workspace token
        """
        # Parse JSON body
        body_data, error_response = parse_json_body(request)
        if error_response:
            return error_response
        
        repository_id = body_data.get('repository_id')
        workspace_id = body_data.get('workspace_id')
        
        if not repository_id or not workspace_id:
            return JsonResponse(
                {'error': 'repository_id and workspace_id are required'}, 
                status=400
            )
        
        logger.info(f"Fetching branches for repository {repository_id} in workspace {workspace_id}")
        
        try:
            # Fetch required details
            repository_details = self.config_client.get_repository(
                workspace_id, repository_id, user_id
            )
            workspace_token = self.config_client.get_workspace_token(workspace_id, user_id)
            
            # Build payload and fetch branches
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


class AnalysisOrchestrator:
    """Orchestrates complex analysis operations"""
    
    def __init__(self, analyze_service_url, collection_service_url):
        self.analyze_service_url = analyze_service_url
        self.collection_service_url = collection_service_url
    
    def create_analysis(self, request, user_id):
        """
        Creates an analysis.
        If no CSV but cleaned_data_id, fetches the CSV from collection service.
        """
        has_csv_file = 'csv_file' in request.FILES
        cleaned_data_id = request.POST.get('cleaned_data_id')
        
        logger.info(f"Analysis create - has_csv_file: {has_csv_file}, cleaned_data_id: {cleaned_data_id}")
        
        # If no CSV but cleaned_data_id: orchestration needed
        if not has_csv_file and cleaned_data_id:
            return self._create_analysis_with_fetched_csv(request, user_id, cleaned_data_id)
        
        # Otherwise: simple proxy
        from ..proxy.base_proxy import BaseProxyHandler
        proxy = BaseProxyHandler(self.analyze_service_url, '/api/analysis')
        return proxy.proxy_request(request, user_id)
    
    def _create_analysis_with_fetched_csv(self, request, user_id, cleaned_data_id):
        """Creates an analysis by first fetching the CSV"""
        
        file_type = request.POST.get('file_type', 'structured')
        
        logger.info(f"Fetching CSV from collection service for cleaned_data_id: {cleaned_data_id}")
        
        try:
            # Fetch CSV
            csv_content, filename = self._fetch_csv_from_collection(
                cleaned_data_id, file_type, user_id
            )
            
            if csv_content is None:
                return JsonResponse(
                    {'error': 'Could not retrieve CSV from collection service'},
                    status=404
                )
            
            logger.info(f"Successfully fetched CSV: {filename}")
            
            # Send analysis with the CSV
            return self._proxy_analysis_with_csv(request, user_id, csv_content, filename)
            
        except Exception as e:
            logger.error(f"Error fetching CSV from collection service: {e}")
            return JsonResponse(
                {'error': 'Failed to fetch CSV from collection service', 'detail': str(e)},
                status=500
            )
    
    def _fetch_csv_from_collection(self, cleaned_data_id, file_type, user_id):
        """Fetches a CSV from the collection service"""
        
        download_url = f"{self.collection_service_url}/cleaned-data/{cleaned_data_id}/download/{file_type}"
        
        logger.info(f"Fetching CSV from: {download_url}")
        
        headers = {'X-User-ID': str(user_id)}
        
        try:
            response = requests.get(download_url, headers=headers, timeout=30)
            
            if response.status_code != 200:
                logger.error(f"Failed to fetch CSV: {response.status_code} - {response.text}")
                return None, None
            
            # Extract filename
            content_disposition = response.headers.get('Content-Disposition', '')
            filename = 'cleaned_data.csv'
            
            if content_disposition and 'filename=' in content_disposition:
                parts = content_disposition.split('filename=')
                if len(parts) > 1:
                    filename = parts[1].strip('"\'')
            
            return response.content, filename
            
        except requests.RequestException as e:
            logger.error(f"Request error fetching CSV: {e}")
            return None, None
    
    def _proxy_analysis_with_csv(self, request, user_id, csv_content, filename):
        """Sends the analysis request with the fetched CSV"""
        
        target_url = f"{self.analyze_service_url.rstrip('/')}/create/"
        
        logger.info(f"Proxying analysis to {target_url} with CSV: {filename}")
        
        headers = {'X-User-ID': str(user_id)}
        
        # Prepare form data (excluding file_type)
        data = []
        for key in request.POST.keys():
            if key == 'file_type':  # Exclude file_type
                continue
            values = request.POST.getlist(key)
            for value in values:
                data.append((key, value))
        
        files = {
            'csv_file': (filename, io.BytesIO(csv_content), 'text/csv')
        }
        
        for key, file in request.FILES.items():
            if key != 'csv_file':
                files[key] = (file.name, file.read(), file.content_type)
        
        try:
            response = requests.post(
                url=target_url,
                headers=headers,
                data=data,
                files=files,
                timeout=60
            )
            
            logger.info(f"Response from analysis service: {response.status_code}")
            
            try:
                response_data = response.json()
            except ValueError:
                response_data = {'detail': response.text or 'Empty response'}
            
            return JsonResponse(response_data, status=response.status_code, safe=False)
            
        except requests.Timeout:
            return JsonResponse(
                {'error': 'Service timeout', 'detail': 'The analysis service took too long to respond'},
                status=504
            )
        except requests.ConnectionError as e:
            return JsonResponse(
                {'error': 'Service unavailable', 'detail': str(e)},
                status=503
            )
        except requests.RequestException as e:
            return JsonResponse(
                {'error': 'Service error', 'detail': str(e)},
                status=503
            )