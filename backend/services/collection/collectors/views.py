"""Collection Views - HTTP orchestration layer."""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, FileResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from .serializers import (
    StartCollectionSerializer,
    MetricsFilterSerializer,
    CollectionSerializer,
    CleanedDataSerializer,
    CreateCleanedDataSerializer,
)
from .models import Collection, CleanedData
from .services import (
    MetricsService,
    BranchService,
    resolve_workspace_token,
    CollectionService,
    CollectedDataService,
    DataCleaningService,
    CleanedDataService,
    CollectionServiceError,
    CollectionStateError,
    CollectionValidationError,
    StorageError,
    UserDatasetsService,
)
from .schema import (
    available_metrics_schema,
    branches_for_repository_schema,
    collection_branches_schema,
    start_collection_schema,
    configure_metrics_schema,
    validate_collection_schema,
    execute_collection_schema,
    collection_status_schema,
    resume_collection_schema,
    collection_plans_list_schema,
    collection_history_schema,
    delete_collection_schema,
    collected_data_schema,
    download_collection_json_schema,
    data_cleaning_config_schema,
    apply_filters_csv_schema,
    collection_cleaned_data_list_schema,
    create_cleaned_data_schema,
    cleaned_data_detail_get_schema,
    cleaned_data_detail_delete_schema,
    download_cleaned_data_csv_schema,
)

import logging
import json
import io

logger = logging.getLogger(__name__)


# =============================================================================
# Helper Mixin for User ID Validation
# =============================================================================


class UserIdRequiredMixin:
    """Mixin for user ID validation."""

    def get_user_id(self, request):
        """Extract user ID from request headers."""
        user_id = request.headers.get("X-User-ID")
        if not user_id:
            return None
        return int(user_id)

    def user_id_error_response(self):
        """Return 401 error response."""
        return Response(
            {"error": "User ID required"}, status=status.HTTP_401_UNAUTHORIZED
        )


# =============================================================================
# Metrics and Branches Views
# =============================================================================


class GetAvailableMetricsView(UserIdRequiredMixin, APIView):
    """Get available metrics for a platform."""

    @available_metrics_schema
    def get(self, request):
        user_id = self.get_user_id(request)
        if not user_id:
            return self.user_id_error_response()

        platform = request.query_params.get("platform", "github")
        repository_id = request.query_params.get("repository_id")

        if not repository_id:
            return Response(
                {"error": "repository_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = MetricsService.get_metrics_with_collection_status(
            user_id=user_id, repository_id=int(repository_id), platform=platform
        )

        response_data = {
            "success": True,
            "available_metrics": result["available_metrics"],
            "platform": result["platform"],
            "has_active_collection": result["has_active_collection"],
        }

        if result["active_collection"]:
            response_data["active_collection"] = CollectionSerializer(
                result["active_collection"]
            ).data

        return Response(response_data)


class GetBranchesForRepositoryView(UserIdRequiredMixin, APIView):
    """Get branches for a repository using provided token."""

    @branches_for_repository_schema
    def post(self, request):
        user_id = self.get_user_id(request)
        if not user_id:
            return self.user_id_error_response()

        platform = request.data.get('platform')
        token = request.data.get('token')
        workspace_id = request.data.get('workspace_id')
        repo_full_name = request.data.get('repository_full_name')
        default_branch = request.data.get('default_branch')

        if not all([platform, repo_full_name]):
            return Response(
                {'error': 'platform and repository_full_name are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not token:
            if not workspace_id:
                return Response(
                    {'error': 'workspace_id is required when token is not provided'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            token = resolve_workspace_token(
                user_id=user_id,
                workspace_id=int(workspace_id),
                platform=platform,
            )

        try:
            branches = BranchService.fetch_branches(
                platform=platform, token=token, repo_full_name=repo_full_name
            )

            return Response(
                {
                    "success": True,
                    "branches": branches,
                    "default_branch": default_branch,
                }
            )

        except CollectionServiceError as e:
            return Response(
                {"success": False, "error": str(e), "branches": []},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class GetBranchesView(UserIdRequiredMixin, APIView):
    """Get branches for a collection repository."""

    @collection_branches_schema
    def get(self, request, plan_id):
        user_id = self.get_user_id(request)
        if not user_id:
            return self.user_id_error_response()

        collection = get_object_or_404(Collection, id=plan_id, user=user_id)

        try:
            branches = BranchService.fetch_branches_for_collection(collection)

            return Response(
                {
                    "success": True,
                    "branches": branches,
                    "default_branch": collection.default_branch,
                }
            )

        except CollectionServiceError as e:
            return Response(
                {"success": False, "error": str(e), "branches": []},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# =============================================================================
# Collection Lifecycle Views
# =============================================================================


class StartCollectionView(UserIdRequiredMixin, APIView):
    """Create or retrieve a collection for a repository (idempotent)."""

    @start_collection_schema
    def post(self, request):
        user_id = self.get_user_id(request)
        if not user_id:
            return self.user_id_error_response()

        serializer = StartCollectionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data
        platform = validated_data["platform"]

        collection, is_existing = CollectionService.get_or_create_collection(
            user_id=user_id, validated_data=validated_data
        )

        available_metrics = MetricsService.get_available_metrics(platform)

        if is_existing:
            return Response(
                {
                    "success": True,
                    "message": "Active collection already exists",
                    "collection_plan": CollectionSerializer(collection).data,
                    "available_metrics": available_metrics,
                    "platform": platform,
                    "is_existing": True,
                },
                status=status.HTTP_200_OK,
            )

        return Response(
            {
                "success": True,
                "message": "Collection created. Now select metrics and filters.",
                "collection_plan": CollectionSerializer(collection).data,
                "available_metrics": available_metrics,
                "platform": platform,
                "is_existing": False,
            },
            status=status.HTTP_201_CREATED,
        )


class ConfigureMetricsView(UserIdRequiredMixin, APIView):
    """Configure metrics, filters, and branch for a collection"""

    @configure_metrics_schema
    def post(self, request, plan_id):
        user_id = self.get_user_id(request)
        if not user_id:
            return self.user_id_error_response()

        collection = get_object_or_404(Collection, id=plan_id, user=user_id)

        serializer = MetricsFilterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data

        try:
            collection = CollectionService.configure_metrics(
                collection=collection,
                selected_metrics=validated_data["selected_metrics"],
                filters=validated_data,
                branch_name=request.data.get("branch_name"),
            )

            return Response(
                {
                    "success": True,
                    "message": "Metrics and filters configured successfully",
                    "collection_plan": CollectionSerializer(collection).data,
                }
            )

        except CollectionStateError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ValidateCollectionPlanView(UserIdRequiredMixin, APIView):
    """Show collection summary before starting collection"""

    @validate_collection_schema
    def get(self, request, plan_id):
        user_id = self.get_user_id(request)
        if not user_id:
            return self.user_id_error_response()

        collection = get_object_or_404(Collection, id=plan_id, user=user_id)

        summary = CollectionService.get_collection_summary(collection)

        return Response(
            {
                "collection_plan": CollectionSerializer(collection).data,
                "summary": summary,
            }
        )


class ExecuteCollectionView(UserIdRequiredMixin, APIView):
    """Start the actual data collection in background"""

    @execute_collection_schema
    def post(self, request, plan_id):
        user_id = self.get_user_id(request)
        if not user_id:
            return self.user_id_error_response()

        collection = get_object_or_404(Collection, id=plan_id, user=user_id)

        try:
            collection = CollectionService.execute_collection(collection)

            return Response(
                {
                    "success": True,
                    "message": "Collection started in background",
                    "collection_plan": CollectionSerializer(collection).data,
                }
            )

        except (CollectionStateError, CollectionValidationError) as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class CollectionStatusView(UserIdRequiredMixin, APIView):
    """Get the status of a collection"""

    @collection_status_schema
    def get(self, request, plan_id=None, collection_id=None):
        user_id = self.get_user_id(request)
        if not user_id:
            return self.user_id_error_response()

        # Support both plan_id and collection_id
        lookup_id = plan_id or collection_id

        collection = get_object_or_404(Collection, id=lookup_id, user=user_id)

        status_data = CollectionService.get_collection_status(collection)

        return Response(
            {"collection_plan": CollectionSerializer(collection).data, **status_data}
        )


class ResumeCollectionView(UserIdRequiredMixin, APIView):
    """Resume a paused or failed collection"""

    @resume_collection_schema
    def post(self, request, plan_id):
        user_id = self.get_user_id(request)
        if not user_id:
            return self.user_id_error_response()

        collection = get_object_or_404(Collection, id=plan_id, user=user_id)

        try:
            collection = CollectionService.resume_collection(collection)

            return Response(
                {
                    "success": True,
                    "message": "Collection resumed",
                    "last_collected_item": collection.last_collected_item_id,
                }
            )

        except CollectionStateError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class CollectionPlanListView(UserIdRequiredMixin, APIView):
    """List all collections for a user"""

    @collection_plans_list_schema
    def get(self, request):
        user_id = self.get_user_id(request)
        if not user_id:
            return self.user_id_error_response()

        collections = CollectionService.get_user_collections(user_id)
        serializer = CollectionSerializer(collections, many=True)

        return Response(serializer.data)


class CollectionHistoryView(UserIdRequiredMixin, APIView):
    """Get collection history for a specific repository"""

    @collection_history_schema
    def get(self, request, repository_id):
        user_id = self.get_user_id(request)
        if not user_id:
            return self.user_id_error_response()

        collections = CollectionService.get_repository_history(
            user_id=user_id, repository_id=repository_id
        )

        serializer = CollectionSerializer(collections, many=True)

        return Response(
            {
                "success": True,
                "collections": serializer.data,
                "total": collections.count(),
            }
        )


class DeleteCollectionView(UserIdRequiredMixin, APIView):
    """Delete a collection and all its related data"""

    @delete_collection_schema
    def delete(self, request, collection_id):
        user_id = self.get_user_id(request)
        if not user_id:
            return self.user_id_error_response()

        collection = get_object_or_404(Collection, id=collection_id, user=user_id)

        try:
            CollectionService.delete_collection(collection)

            return Response(
                {
                    "success": True,
                    "message": "Collection and all related data deleted successfully",
                }
            )

        except StorageError as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# =============================================================================
# Collected Data Views
# =============================================================================


class CollectedDataView(UserIdRequiredMixin, APIView):
    """Get collected data for a collection from MinIO"""

    @collected_data_schema
    def get(self, request, plan_id):
        user_id = self.get_user_id(request)
        if not user_id:
            return self.user_id_error_response()

        collection = get_object_or_404(Collection, id=plan_id, user=user_id)

        try:
            result = CollectedDataService.get_collected_data(collection)

            if not result.get("found", True):
                return Response(result, status=status.HTTP_404_NOT_FOUND)

            return Response(result)

        except StorageError as e:
            return Response(
                {"error": "Failed to retrieve collected data", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class DownloadCollectionJSONView(UserIdRequiredMixin, APIView):
    """Download raw JSON data from a collection"""

    @download_collection_json_schema
    def get(self, request, collection_id):
        user_id = self.get_user_id(request)
        if not user_id:
            return self.user_id_error_response()

        collection = get_object_or_404(Collection, id=collection_id, user=user_id)

        if not collection.raw_data_filename:
            return Response(
                {"error": "No data file available"}, status=status.HTTP_404_NOT_FOUND
            )

        json_data = CollectedDataService.get_raw_json(collection)

        if json_data is None:
            return Response(
                {"error": "File not found in storage"}, status=status.HTTP_404_NOT_FOUND
            )

        response = HttpResponse(
            json.dumps(json_data, indent=2), content_type="application/json"
        )
        response["Content-Disposition"] = (
            f'attachment; filename="{collection.raw_data_filename}"'
        )
        response["Access-Control-Expose-Headers"] = "Content-Disposition"
        return response


# =============================================================================
# Data Cleaning Views
# =============================================================================


class DataCleaningConfigView(UserIdRequiredMixin, APIView):
    """Get current data for cleaning configuration"""

    @data_cleaning_config_schema
    def get(self, request, plan_id):
        user_id = self.get_user_id(request)
        if not user_id:
            return self.user_id_error_response()

        collection = get_object_or_404(Collection, id=plan_id, user=user_id)

        try:
            config = DataCleaningService.get_cleaning_config(collection)

            return Response({"success": True, **config})

        except CollectionStateError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except StorageError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)


class ApplyFiltersAndCreateCSVView(UserIdRequiredMixin, APIView):
    """Apply filters and create structured CSV"""

    @apply_filters_csv_schema
    def post(self, request, plan_id):
        user_id = self.get_user_id(request)
        if not user_id:
            return self.user_id_error_response()

        collection = get_object_or_404(Collection, id=plan_id, user=user_id)

        filters = {
            "file_extensions": request.data.get("file_extensions", []),
            "authors": request.data.get("authors", []),
            "keyword_field": request.data.get("keyword_field"),
            "keywords": request.data.get("keywords", []),
            "replace_json": request.data.get("replace_json", False),
        }

        try:
            result = DataCleaningService.apply_filters_and_create_csv(
                collection=collection, filters=filters
            )

            return Response(
                {
                    "success": True,
                    "message": "Structured CSV created successfully",
                    **result,
                }
            )

        except StorageError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error creating CSV: {e}")
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# =============================================================================
# CleanedData Views
# =============================================================================


class CollectionCleanedDataListView(UserIdRequiredMixin, APIView):
    """Get all cleaned data for a collection"""

    @collection_cleaned_data_list_schema
    def get(self, request, collection_id):
        user_id = self.get_user_id(request)
        if not user_id:
            return self.user_id_error_response()

        collection = get_object_or_404(Collection, id=collection_id, user=user_id)

        cleaned_data_list = CleanedDataService.get_cleaned_data_list(collection)
        serializer = CleanedDataSerializer(cleaned_data_list, many=True)

        return Response(
            {
                "success": True,
                "cleaned_data": serializer.data,
                "collection": {
                    "id": collection.id,
                    "repository_name": collection.repository_name,
                    "status": collection.status,
                },
            }
        )


class CreateCleanedDataView(UserIdRequiredMixin, APIView):
    """Create a new cleaned data instance"""

    @create_cleaned_data_schema
    def post(self, request):
        user_id = self.get_user_id(request)
        if not user_id:
            return self.user_id_error_response()

        serializer = CreateCleanedDataSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data
        collection_id = validated_data["collection_id"]

        collection = get_object_or_404(Collection, id=collection_id, user=user_id)

        try:
            cleaned_data = CleanedDataService.create_cleaned_data(
                collection=collection,
                start_date=validated_data.get('start_date'),
                end_date=validated_data.get('end_date'),
                filters=validated_data.get('filters'),
                selected_features=validated_data.get('selected_features')
            )

            return Response(
                {
                    "success": True,
                    "message": "Cleaning and Filtering Successful",
                    "cleaned_data": CleanedDataSerializer(cleaned_data).data,
                },
                status=status.HTTP_201_CREATED,
            )

        except CollectionStateError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except (StorageError, Exception) as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CleanedDataDetailView(UserIdRequiredMixin, APIView):
    """Get details of a specific cleaned data instance"""

    @cleaned_data_detail_get_schema
    def get(self, request, cleaned_data_id):
        user_id = self.get_user_id(request)
        if not user_id:
            return self.user_id_error_response()

        cleaned_data = get_object_or_404(CleanedData, id=cleaned_data_id)

        if cleaned_data.collection.user != user_id:
            return Response(
                {"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN
            )

        serializer = CleanedDataSerializer(cleaned_data)
        return Response(serializer.data)

    @cleaned_data_detail_delete_schema
    def delete(self, request, cleaned_data_id):
        """Delete a cleaned data instance"""
        user_id = self.get_user_id(request)
        if not user_id:
            return self.user_id_error_response()

        cleaned_data = get_object_or_404(CleanedData, id=cleaned_data_id)

        if cleaned_data.collection.user != user_id:
            return Response(
                {"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN
            )

        try:
            CleanedDataService.delete_cleaned_data(cleaned_data)

            return Response(
                {"success": True, "message": "Cleaned data deleted successfully"}
            )
        except StorageError as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@method_decorator(csrf_exempt, name="dispatch")
class DownloadCleanedDataCSVView(View):
    """Download CSV file from a cleaned data instance."""

    @download_cleaned_data_csv_schema
    def get(self, request, cleaned_data_id, file_type):
        user_id = request.headers.get("X-User-ID")
        if not user_id:
            return HttpResponse(
                '{"error": "User ID required"}',
                status=401,
                content_type="application/json",
            )

        try:
            cleaned_data = CleanedData.objects.get(id=cleaned_data_id)
        except CleanedData.DoesNotExist:
            return HttpResponse(
                '{"error": "Cleaned data not found"}',
                status=404,
                content_type="application/json",
            )

        if cleaned_data.collection.user != int(user_id):
            return HttpResponse(
                '{"error": "Permission denied"}',
                status=403,
                content_type="application/json",
            )

        try:
            csv_bytes = CleanedDataService.get_csv_for_download(cleaned_data, file_type)
        except CollectionValidationError:
            return HttpResponse(
                '{"error": "Invalid file type"}',
                status=400,
                content_type="application/json",
            )

        if csv_bytes is None:
            return HttpResponse(
                '{"error": "File not found in storage"}',
                status=404,
                content_type="application/json",
            )

        filename = (
            cleaned_data.structured_csv_filename
            if file_type == "structured"
            else cleaned_data.statistics_csv_filename
        )

        file_like = io.BytesIO(csv_bytes)
        response = FileResponse(
            file_like, as_attachment=True, filename=filename, content_type="text/csv"
        )
        return response


class UserDatasetsView(APIView):
    """
    Get all datasets (collections and cleaned data) for a user
    """

    def get(self, request):
        user_id = request.headers.get("X-User-ID")

        if not user_id:
            return Response(
                {"error": "X-User-ID header is required"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            user_id = int(user_id)
        except (ValueError, TypeError):
            return Response(
                {"error": "Invalid user_id format"}, status=status.HTTP_400_BAD_REQUEST
            )

        logger.info(f"Fetching datasets for user {user_id}")

        collections_query = Collection.objects.filter(user=user_id)

        collections = collections_query.select_related().prefetch_related(
            "cleaned_data"
        )

        # Serialize data
        collections_data = CollectionSerializer(collections, many=True).data

        response_data = {
            "user_id": user_id,
            "total_collections": collections.count(),
            "collections": collections_data,
        }

        cleaned_data_list = []
        for collection in collections:
            cleaned_items = collection.cleaned_data.all()
            for cleaned in cleaned_items:
                cleaned_data_list.append(
                    {
                        **CleanedDataSerializer(cleaned).data,
                        "collection_id": collection.id,
                        "repository_name": collection.repository_name,
                        "repository_full_name": collection.repository_full_name,
                        "platform": collection.platform,
                        "repository_url": collection.repository_url,
                        "repository_id": collection.repository_id,
                        "workspace_id": collection.workspace_id,
                    }
                )

        response_data["total_cleaned_datasets"] = len(cleaned_data_list)
        response_data["cleaned_datasets"] = cleaned_data_list

        # Global statistics
        response_data["statistics"] = {
            "total_items_collected": sum(c.collected_items for c in collections),
            "active_collections": collections.filter(
                status__in=Collection.ACTIVE_STATUSES
            ).count(),
            "completed_collections": collections.filter(status="completed").count(),
            "failed_collections": collections.filter(status="failed").count(),
        }

        logger.info(f"Returning {collections.count()} collections for user {user_id}")

        return Response(response_data, status=status.HTTP_200_OK)


# =============================================================================
# External Upload View
# =============================================================================

class UploadExternalCollectionView(UserIdRequiredMixin, APIView):
    """Upload an externally collected JSON file as a new collection.

    Designed for large files (up to 6 GB).  The uploaded file is streamed
    directly from Django's temp-file to MinIO — it is never fully loaded
    into memory.
    """

    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        user_id = self.get_user_id(request)
        if not user_id:
            return self.user_id_error_response()

        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return Response(
                {'error': 'No file provided. Send a JSON file as "file".'},
                status=status.HTTP_400_BAD_REQUEST
            )

        platform = request.POST.get('platform', '').lower()
        if platform not in ('github', 'gitlab'):
            return Response(
                {'error': 'Platform must be "github" or "gitlab".'},
                status=status.HTTP_400_BAD_REQUEST
            )

        name = request.POST.get('name', 'external-upload').strip()

        # ---- Lightweight JSON validation (read only the first bytes) ----
        first_chunk = uploaded_file.read(1024)
        stripped = first_chunk.lstrip()
        if not stripped or stripped[0:1] not in (b'{', b'['):
            return Response(
                {'error': 'File does not appear to be valid JSON (must start with { or [).'},
                status=status.HTTP_400_BAD_REQUEST
            )
        uploaded_file.seek(0)  # rewind for MinIO upload

        # ---- Stream the file directly to MinIO ----
        file_size = uploaded_file.size

        from .minio_client import MinIOClient
        minio_client = MinIOClient()

        # Create DB record first (need the id for the filename)
        collection = Collection.objects.create(
            user=user_id,
            workspace_id=0,
            repository_id=0,
            repository_name=name,
            repository_full_name=f"external/{name}",
            platform=platform,
            token_encrypted='',
            status='completed',
            total_items=0,
            collected_items=0,
            is_external=True,
        )

        filename = minio_client.generate_filename(name, collection.id, 'json')

        try:
            saved = minio_client.save_stream(uploaded_file, filename, file_size)
        except Exception as exc:
            logger.error(f"MinIO streaming upload failed: {exc}")
            collection.delete()
            return Response(
                {'error': 'Failed to store file. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        if not saved:
            collection.delete()
            return Response(
                {'error': 'Failed to store file. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        collection.raw_data_filename = filename
        collection.save(update_fields=['raw_data_filename'])

        # Stream-extract cleaning metadata (authors, extensions, count) without
        # loading the full file into memory.
        try:
            from .metadata_extractor import extract_cleaning_metadata
            obj_stream = minio_client.get_object_stream(filename)
            if obj_stream:
                try:
                    metadata = extract_cleaning_metadata(obj_stream, platform)
                    collection.cleaning_metadata = metadata
                    collection.total_items = metadata.get('total_items', 0)
                    collection.collected_items = collection.total_items
                    collection.save(update_fields=['cleaning_metadata', 'total_items', 'collected_items'])
                finally:
                    obj_stream.close()
                    obj_stream.release_conn()
        except Exception as exc:
            logger.warning(f"Metadata extraction failed (non-fatal): {exc}")

        serializer = CollectionSerializer(collection)
        return Response({
            'success': True,
            'message': 'External collection uploaded successfully.',
            'collection': serializer.data,
        }, status=status.HTTP_201_CREATED)


class UserDatasetsView(UserIdRequiredMixin, APIView):
    """Get all datasets (collections and cleaned data) for a user."""
    
    def get(self, request):
        user_id = self.get_user_id(request)
        
        if not user_id:
            return self.user_id_error_response()
        
        try:
            response_data = UserDatasetsService.get_user_datasets(user_id)
            return Response(response_data, status=status.HTTP_200_OK)
            
        except ValueError as e:
            return Response(
                {'error': 'Invalid user_id format'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error fetching user datasets: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

# =============================================================================
# Backward Compatibility Aliases
# =============================================================================

CollectionCleaningsListView = CollectionCleanedDataListView
CreateCleaningView = CreateCleanedDataView
CleaningDetailView = CleanedDataDetailView
DownloadCleaningCSVView = DownloadCleanedDataCSVView

DownloadCleaningCSVView = DownloadCleanedDataCSVView
