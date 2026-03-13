import logging
from django.conf import settings

from .routing.handlers import (
    CollectionRequestHandler,
    AnalysisRequestHandler,
    WorkspaceRequestHandler,
)
from .services.service_clients import (
    ConfigurationServiceClient,
    CollectionServiceClient,
)

logger = logging.getLogger(__name__)


class ServiceProxyMiddleware:
    """
    Main routing middleware.
    Delegates requests to specialized handlers.
    """

    def __init__(self, get_response):
        self.get_response = get_response

        # URLs des services
        self.configuration_service_url = getattr(
            settings,
            "CONFIGURATION_SERVICE_URL",
            "http://configuration-service:8001/api/workspaces",
        )

        self.collection_service_url = getattr(
            settings,
            "COLLECTION_SERVICE_URL",
            "http://collection-service:8002/api/collections",
        )

        self.analyze_service_url = getattr(
            settings, "ANALYZE_SERVICE_URL", "http://analyze-service:8003/api/analysis"
        )

        # Initialization of service clients
        self.config_client = ConfigurationServiceClient(self.configuration_service_url)
        self.collection_client = CollectionServiceClient(self.collection_service_url)

        # Initialization of handlers
        self.workspace_handler = WorkspaceRequestHandler(self.configuration_service_url)

        self.collection_handler = CollectionRequestHandler(
            self.collection_service_url, self.config_client, self.collection_client
        )

        self.analysis_handler = AnalysisRequestHandler(
            self.analyze_service_url, self.collection_service_url
        )

        logger.info("ServiceProxyMiddleware initialized")
        logger.info(f"   Configuration Service: {self.configuration_service_url}")
        logger.info(f"   Collection Service: {self.collection_service_url}")
        logger.info(f"   Analysis Service: {self.analyze_service_url}")

    def __call__(self, request):
        """Route les requêtes vers le handler approprié"""

        # Workspace endpoints
        if request.path.startswith("/api/workspaces"):
            return self.workspace_handler.handle(request)

        # Collection endpoints
        if request.path.startswith("/api/collections"):
            return self.collection_handler.handle(request)

        # Analysis endpoints
        if request.path.startswith("/api/analysis"):
            return self.analysis_handler.handle(request)

        # Other non-proxied requests
        return self.get_response(request)
