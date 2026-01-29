import logging
from django.http import JsonResponse

from ..auth.token_utils import extract_user_from_request
from ..proxy.base_proxy import BaseProxyHandler
from ..services.orchestrators import (
    CollectionOrchestrator,
    AnalysisOrchestrator
)

logger = logging.getLogger(__name__)


class WorkspaceRequestHandler:
    """Handler for workspace requests (simple proxy)"""
    
    def __init__(self, service_url):
        self.proxy = BaseProxyHandler(service_url, '/api/workspaces')
    
    def handle(self, request):
        """Proxy direct vers le service de configuration"""
        return self.proxy.proxy_request(request)


class CollectionRequestHandler:
    """Handler for collection requests"""
    
    def __init__(self, service_url, config_client, collection_client):
        self.proxy = BaseProxyHandler(service_url, '/api/collections')
        self.orchestrator = CollectionOrchestrator(config_client, collection_client)
    
    def handle(self, request):
        """Route to orchestrator or simple proxy based on endpoint"""
        
        # Token extraction and validation
        user_id, error_response = extract_user_from_request(request)
        if error_response:
            return error_response
        
        # Endpoint /start requires orchestration
        if request.path == '/api/collections/start' and request.method == 'POST':
            return self.orchestrator.start_collection(request, user_id)
        
        # Endpoint /branches requires orchestration
        if request.path == '/api/collections/branches/' and request.method == 'POST':
            return self.orchestrator.get_branches(request, user_id)
        
        # Other endpoints: simple proxy
        return self.proxy.proxy_request(request, user_id)


class AnalysisRequestHandler:
    """Handler for analysis requests"""
    
    def __init__(self, service_url, collection_service_url):
        self.proxy = BaseProxyHandler(service_url, '/api/analysis')
        self.orchestrator = AnalysisOrchestrator(service_url, collection_service_url)
    
    def handle(self, request):
        """Route to orchestrator or simple proxy based on endpoint"""
        
        # Token extraction and validation
        user_id, error_response = extract_user_from_request(request)
        if error_response:
            return error_response
        
        # Endpoint /create may require orchestration
        if (request.path == '/api/analysis/create/' or 
            request.path == '/api/analysis/create') and request.method == 'POST':
            return self.orchestrator.create_analysis(request, user_id)
        
        # Other endpoints: simple proxy
        return self.proxy.proxy_request(request, user_id)