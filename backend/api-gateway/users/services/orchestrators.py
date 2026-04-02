import io
import logging
import requests
from django.http import JsonResponse

from ..utils.request_utils import parse_json_body
from .collection_automation import (
    DEFAULT_LLM_MODEL,
    CollectionAutomationValidationError,
    build_collection_automation_debug_context,
    build_llm_collection_prompt,
    normalize_collection_automation_payload,
    sanitize_user_prompt,
)
from .service_clients import (
    ServiceClientError,
    build_collection_payload,
    build_branches_payload,
)

logger = logging.getLogger(__name__)


class CollectionOrchestrator:
    def __init__(self, config_client, collection_client, llm_client):
        self.config_client = config_client
        self.collection_client = collection_client
        self.llm_client = llm_client

    def start_collection(self, request, user_id):
        """
        Starts a collection.
        Requires: repository details + workspace token
        """
        # Parse JSON body
        body_data, error_response = parse_json_body(request)
        if error_response:
            return error_response

        repository_id = body_data.get("repository_id")
        workspace_id = body_data.get("workspace_id")

        if not repository_id or not workspace_id:
            return JsonResponse(
                {"error": "repository_id and workspace_id are required"}, status=400
            )

        logger.info(
            f"Starting collection for repository {repository_id} in workspace {workspace_id}"
        )

        try:
            # Fetch required details
            repository_details = self.config_client.get_repository(
                workspace_id, repository_id, user_id
            )
            
            # Build payload and start collection
            collection_payload = build_collection_payload(
                repository_details, repository_id, workspace_id
            )
            response_data, status_code = self.collection_client.start_collection(
                collection_payload, user_id
            )

            return JsonResponse(response_data, status=status_code)

        except ServiceClientError as e:
            error_response = {"error": e.message}
            if e.detail:
                error_response["detail"] = e.detail
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

        repository_id = body_data.get("repository_id")
        workspace_id = body_data.get("workspace_id")

        if not repository_id or not workspace_id:
            return JsonResponse(
                {"error": "repository_id and workspace_id are required"}, status=400
            )

        logger.info(
            f"Fetching branches for repository {repository_id} in workspace {workspace_id}"
        )

        try:
            # Fetch required details
            repository_details = self.config_client.get_repository(
                workspace_id, repository_id, user_id
            )
            
            # Build payload and fetch branches
            branches_payload = build_branches_payload(repository_details, workspace_id)
            response_data, status_code = self.collection_client.get_branches(
                branches_payload, user_id
            )

            return JsonResponse(response_data, status=status_code)

        except ServiceClientError as e:
            error_response = {"error": e.message}
            if e.detail:
                error_response["detail"] = e.detail
            return JsonResponse(error_response, status=e.status_code)

    def preview_automatic_collection(self, request, user_id):
        """Generate, validate, and normalize an automatic collection draft."""
        body_data, error_response = parse_json_body(request)
        if error_response:
            return error_response

        repository_id = body_data.get("repository_id")
        workspace_id = body_data.get("workspace_id")
        model = body_data.get("model") or DEFAULT_LLM_MODEL

        try:
            prompt = sanitize_user_prompt(body_data.get("prompt"))
        except CollectionAutomationValidationError as exc:
            return JsonResponse({"error": str(exc)}, status=400)

        if not repository_id or not workspace_id:
            return JsonResponse(
                {"error": "repository_id and workspace_id are required"},
                status=400,
            )

        logger.info(
            "Generating automatic collection draft for repository=%s workspace=%s model=%s prompt_length=%s",
            repository_id,
            workspace_id,
            model,
            len(prompt),
        )

        try:
            llm_response = None
            repository_details = self.config_client.get_repository(
                workspace_id, repository_id, user_id
            )
            llm_prompt = build_llm_collection_prompt(repository_details, prompt)
            llm_response, llm_status = self.llm_client.generate_collection_draft(
                prompt=llm_prompt,
                model=model,
            )

            if llm_status >= 400:
                detail = llm_response.get("detail") if isinstance(llm_response, dict) else None
                error_body = {
                    "error": "Failed to generate automatic draft",
                    "detail": detail or llm_response,
                }
                return JsonResponse(error_body, status=llm_status)
            
            branches_payload = build_branches_payload(repository_details, workspace_id)
            branches_response, branches_status = self.collection_client.get_branches(
                branches_payload,
                user_id,
            )
            available_branches = []
            if branches_status < 400 and isinstance(branches_response, dict):
                available_branches = branches_response.get("branches") or []
            else:
                logger.warning(
                    "Could not fetch branches for automatic draft validation: status=%s",
                    branches_status,
                )

            normalized = normalize_collection_automation_payload(
                llm_payload=llm_response,
                repository_details=repository_details,
                available_branches=available_branches,
            )

            normalized["available_branches"] = available_branches
            return JsonResponse({"success": True, **normalized}, status=200)

        except CollectionAutomationValidationError as exc:
            debug_context = build_collection_automation_debug_context(llm_response)
            logger.warning(
                "Automatic draft validation failed for repository=%s workspace=%s: %s | debug=%s",
                repository_id,
                workspace_id,
                exc,
                debug_context,
            )
            return JsonResponse(
                {
                    "error": str(exc),
                    "detail": debug_context,
                },
                status=422,
            )
        except ServiceClientError as e:
            error_body = {"error": e.message}
            if e.detail:
                error_body["detail"] = e.detail
            return JsonResponse(error_body, status=e.status_code)


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
        has_csv_file = "csv_file" in request.FILES
        cleaned_data_id = request.POST.get("cleaned_data_id")

        logger.info(
            f"Analysis create - has_csv_file: {has_csv_file}, cleaned_data_id: {cleaned_data_id}"
        )

        # If no CSV but cleaned_data_id: orchestration needed
        if not has_csv_file and cleaned_data_id:
            return self._create_analysis_with_fetched_csv(
                request, user_id, cleaned_data_id
            )

        # Otherwise: simple proxy
        from ..proxy.base_proxy import BaseProxyHandler

        proxy = BaseProxyHandler(self.analyze_service_url, "/api/analysis")
        return proxy.proxy_request(request, user_id)

    def _create_analysis_with_fetched_csv(self, request, user_id, cleaned_data_id):
        """Creates an analysis by first fetching the CSV"""

        file_type = request.POST.get("file_type", "structured")

        logger.info(
            f"Fetching CSV from collection service for cleaned_data_id: {cleaned_data_id}"
        )

        try:
            # Fetch CSV
            csv_content, filename = self._fetch_csv_from_collection(
                cleaned_data_id, file_type, user_id
            )

            if csv_content is None:
                return JsonResponse(
                    {"error": "Could not retrieve CSV from collection service"},
                    status=404,
                )

            logger.info(f"Successfully fetched CSV: {filename}")

            # Send analysis with the CSV
            return self._proxy_analysis_with_csv(
                request, user_id, csv_content, filename
            )

        except Exception as e:
            logger.error(f"Error fetching CSV from collection service: {e}")
            return JsonResponse(
                {
                    "error": "Failed to fetch CSV from collection service",
                    "detail": str(e),
                },
                status=500,
            )

    def _fetch_csv_from_collection(self, cleaned_data_id, file_type, user_id):
        """Fetches a CSV from the collection service"""

        download_url = f"{self.collection_service_url}/cleaned-data/{cleaned_data_id}/download/{file_type}"

        logger.info(f"Fetching CSV from: {download_url}")

        headers = {"X-User-ID": str(user_id)}

        try:
            response = requests.get(download_url, headers=headers, timeout=30)

            if response.status_code != 200:
                logger.error(
                    f"Failed to fetch CSV: {response.status_code} - {response.text}"
                )
                return None, None

            # Extract filename
            content_disposition = response.headers.get("Content-Disposition", "")
            filename = "cleaned_data.csv"

            if content_disposition and "filename=" in content_disposition:
                parts = content_disposition.split("filename=")
                if len(parts) > 1:
                    filename = parts[1].strip("\"'")

            return response.content, filename

        except requests.RequestException as e:
            logger.error(f"Request error fetching CSV: {e}")
            return None, None

    def _proxy_analysis_with_csv(self, request, user_id, csv_content, filename):
        """Sends the analysis request with the fetched CSV"""

        target_url = f"{self.analyze_service_url.rstrip('/')}/create/"

        logger.info(f"Proxying analysis to {target_url} with CSV: {filename}")

        headers = {"X-User-ID": str(user_id)}

        # Prepare form data (excluding file_type)
        data = []
        for key in request.POST.keys():
            if key == "file_type":  # Exclude file_type
                continue
            values = request.POST.getlist(key)
            for value in values:
                data.append((key, value))

        files = {"csv_file": (filename, io.BytesIO(csv_content), "text/csv")}

        for key, file in request.FILES.items():
            if key != "csv_file":
                files[key] = (file.name, file.read(), file.content_type)

        try:
            response = requests.post(
                url=target_url, headers=headers, data=data, files=files, timeout=60
            )

            logger.info(f"Response from analysis service: {response.status_code}")

            try:
                response_data = response.json()
            except ValueError:
                response_data = {"detail": response.text or "Empty response"}

            return JsonResponse(response_data, status=response.status_code, safe=False)

        except requests.Timeout:
            return JsonResponse(
                {
                    "error": "Service timeout",
                    "detail": "The analysis service took too long to respond",
                },
                status=504,
            )
        except requests.ConnectionError as e:
            return JsonResponse(
                {"error": "Service unavailable", "detail": str(e)}, status=503
            )
        except requests.RequestException as e:
            return JsonResponse(
                {"error": "Service error", "detail": str(e)}, status=503
            )
