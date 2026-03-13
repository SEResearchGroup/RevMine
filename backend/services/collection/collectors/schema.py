# schema.py
"""
OpenAPI schema definitions for the Collection Service API.
Uses drf-spectacular for documentation generation.
"""

from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter,
    OpenApiExample,
    OpenApiResponse,
    inline_serializer,
)
from drf_spectacular.types import OpenApiTypes
from rest_framework import serializers

from .serializers import (
    StartCollectionSerializer,
    MetricsFilterSerializer,
    CollectionSerializer,
    CleanedDataSerializer,
    CreateCleanedDataSerializer,
)


# =============================================================================
# Metrics and Branches Schemas
# =============================================================================

available_metrics_schema = extend_schema(
    summary="Get available metrics",
    description=(
        "Retrieve available metrics for a specific platform and repository. "
        "Also checks if there's an active collection for the repository."
    ),
    tags=["Metrics & Branches"],
    parameters=[
        OpenApiParameter(
            name="platform",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description="Platform type (github or gitlab)",
            enum=["github", "gitlab"],
            default="github",
        ),
        OpenApiParameter(
            name="repository_id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description="Repository ID from Configuration Service",
            required=True,
        ),
    ],
    responses={
        200: OpenApiTypes.OBJECT,
        400: OpenApiTypes.OBJECT,
        401: OpenApiTypes.OBJECT,
    },
    examples=[
        OpenApiExample(
            "Success Response",
            value={
                "success": True,
                "available_metrics": [
                    {
                        "id": "pull_requests",
                        "name": "Pull Requests",
                        "description": "Collect pull request data",
                        "category": "code_review",
                    },
                    {
                        "id": "commits",
                        "name": "Commits",
                        "description": "Collect commit history",
                        "category": "version_control",
                    },
                ],
                "platform": "github",
                "has_active_collection": False,
            },
            response_only=True,
        ),
        OpenApiExample(
            "With Active Collection",
            value={
                "success": True,
                "available_metrics": [],
                "platform": "github",
                "has_active_collection": True,
                "active_collection": {
                    "id": 1,
                    "status": "in_progress",
                    "progress_percentage": 45,
                },
            },
            response_only=True,
        ),
    ],
)


branches_for_repository_schema = extend_schema(
    summary="Get branches for a repository",
    description=(
        "Fetch all branches from a repository using the provided token. "
        "Used during collection setup to select a specific branch."
    ),
    tags=["Metrics & Branches"],
    request=inline_serializer(
        name="BranchesRequest",
        fields={
            "platform": serializers.CharField(
                help_text="Platform type (github/gitlab)"
            ),
            "token": serializers.CharField(help_text="Access token for the platform"),
            "repository_full_name": serializers.CharField(
                help_text="Full repository name (owner/repo)"
            ),
            "default_branch": serializers.CharField(
                required=False, help_text="Default branch name"
            ),
        },
    ),
    responses={
        200: OpenApiTypes.OBJECT,
        400: OpenApiTypes.OBJECT,
        401: OpenApiTypes.OBJECT,
        500: OpenApiTypes.OBJECT,
    },
    examples=[
        OpenApiExample(
            "Request Example",
            value={
                "platform": "github",
                "token": "ghp_xxxxxxxxxxxx",
                "repository_full_name": "username/my-repo",
                "default_branch": "main",
            },
            request_only=True,
        ),
        OpenApiExample(
            "Success Response",
            value={
                "success": True,
                "branches": ["main", "develop", "feature/new-feature"],
                "default_branch": "main",
            },
            response_only=True,
        ),
    ],
)


collection_branches_schema = extend_schema(
    summary="Get branches for a collection",
    description="Fetch branches for an existing collection's repository.",
    tags=["Metrics & Branches"],
    parameters=[
        OpenApiParameter(
            name="plan_id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Collection plan ID",
        ),
    ],
    responses={
        200: OpenApiTypes.OBJECT,
        401: OpenApiTypes.OBJECT,
        404: OpenApiTypes.OBJECT,
        500: OpenApiTypes.OBJECT,
    },
    examples=[
        OpenApiExample(
            "Success Response",
            value={
                "success": True,
                "branches": ["main", "develop", "feature/auth"],
                "default_branch": "main",
            },
            response_only=True,
        ),
    ],
)


# =============================================================================
# Collection Lifecycle Schemas
# =============================================================================

start_collection_schema = extend_schema(
    summary="Start a new collection",
    description=(
        "Create or retrieve a collection for a repository. "
        "This is idempotent - if an active collection exists, it returns that collection."
    ),
    tags=["Collection Workflow"],
    request=StartCollectionSerializer,
    responses={
        200: OpenApiTypes.OBJECT,
        201: OpenApiTypes.OBJECT,
        400: OpenApiTypes.OBJECT,
        401: OpenApiTypes.OBJECT,
    },
    examples=[
        OpenApiExample(
            "Request Example",
            value={
                "repository_id": 123,
                "workspace_id": 1,
                "repository_name": "my-repo",
                "repository_full_name": "username/my-repo",
                "platform": "github",
                "repository_url": "https://github.com/username/my-repo",
                "default_branch": "main",
                "token": "ghp_xxxxxxxxxxxx",
            },
            request_only=True,
        ),
        OpenApiExample(
            "Created Response",
            value={
                "success": True,
                "message": "Collection created. Now select metrics and filters.",
                "collection_plan": {
                    "id": 1,
                    "repository_name": "my-repo",
                    "status": "pending",
                },
                "available_metrics": [
                    {"id": "pull_requests", "name": "Pull Requests"},
                ],
                "platform": "github",
                "is_existing": False,
            },
            response_only=True,
        ),
        OpenApiExample(
            "Existing Collection Response",
            value={
                "success": True,
                "message": "Active collection already exists",
                "collection_plan": {
                    "id": 1,
                    "repository_name": "my-repo",
                    "status": "in_progress",
                },
                "available_metrics": [],
                "platform": "github",
                "is_existing": True,
            },
            response_only=True,
        ),
    ],
)


configure_metrics_schema = extend_schema(
    summary="Configure collection metrics and filters",
    description=(
        "Set the metrics to collect and apply filters such as date range and branch. "
        "Must be done before executing the collection."
    ),
    tags=["Collection Workflow"],
    parameters=[
        OpenApiParameter(
            name="plan_id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Collection plan ID",
        ),
    ],
    request=MetricsFilterSerializer,
    responses={
        200: OpenApiTypes.OBJECT,
        400: OpenApiTypes.OBJECT,
        401: OpenApiTypes.OBJECT,
        404: OpenApiTypes.OBJECT,
    },
    examples=[
        OpenApiExample(
            "Request Example",
            value={
                "selected_metrics": ["pull_requests", "commits"],
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
                "branch_name": "main",
            },
            request_only=True,
        ),
        OpenApiExample(
            "Success Response",
            value={
                "success": True,
                "message": "Metrics and filters configured successfully",
                "collection_plan": {
                    "id": 1,
                    "selected_metrics": ["pull_requests", "commits"],
                    "status": "pending",
                },
            },
            response_only=True,
        ),
    ],
)


validate_collection_schema = extend_schema(
    summary="Validate collection plan",
    description=(
        "Get a summary of the collection configuration before starting. "
        "Shows what will be collected based on current settings."
    ),
    tags=["Collection Workflow"],
    parameters=[
        OpenApiParameter(
            name="plan_id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Collection plan ID",
        ),
    ],
    responses={
        200: OpenApiTypes.OBJECT,
        401: OpenApiTypes.OBJECT,
        404: OpenApiTypes.OBJECT,
    },
    examples=[
        OpenApiExample(
            "Success Response",
            value={
                "collection_plan": {
                    "id": 1,
                    "repository_name": "my-repo",
                    "status": "pending",
                    "selected_metrics": ["pull_requests"],
                },
                "summary": {
                    "repository": "username/my-repo",
                    "metrics_count": 1,
                    "estimated_items": 150,
                    "date_range": "2024-01-01 to 2024-12-31",
                },
            },
            response_only=True,
        ),
    ],
)


execute_collection_schema = extend_schema(
    summary="Execute the collection",
    description=(
        "Start the actual data collection process in the background. "
        "The collection must have metrics configured before execution."
    ),
    tags=["Collection Workflow"],
    parameters=[
        OpenApiParameter(
            name="plan_id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Collection plan ID",
        ),
    ],
    request=None,
    responses={
        200: OpenApiTypes.OBJECT,
        400: OpenApiTypes.OBJECT,
        401: OpenApiTypes.OBJECT,
        404: OpenApiTypes.OBJECT,
    },
    examples=[
        OpenApiExample(
            "Success Response",
            value={
                "success": True,
                "message": "Collection started in background",
                "collection_plan": {
                    "id": 1,
                    "status": "in_progress",
                    "progress_percentage": 0,
                },
            },
            response_only=True,
        ),
        OpenApiExample(
            "Validation Error",
            value={
                "error": "No metrics selected for collection",
            },
            response_only=True,
        ),
    ],
)


collection_status_schema = extend_schema(
    summary="Get collection status",
    description="Retrieve the current status and progress of a collection.",
    tags=["Collection Management"],
    parameters=[
        OpenApiParameter(
            name="plan_id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Collection plan ID",
            required=False,
        ),
        OpenApiParameter(
            name="collection_id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Collection ID (alternative to plan_id)",
            required=False,
        ),
    ],
    responses={
        200: OpenApiTypes.OBJECT,
        401: OpenApiTypes.OBJECT,
        404: OpenApiTypes.OBJECT,
    },
    examples=[
        OpenApiExample(
            "In Progress Response",
            value={
                "collection_plan": {
                    "id": 1,
                    "status": "in_progress",
                    "progress_percentage": 65,
                    "collected_items": 130,
                    "total_items": 200,
                },
                "is_complete": False,
                "can_resume": False,
            },
            response_only=True,
        ),
        OpenApiExample(
            "Completed Response",
            value={
                "collection_plan": {
                    "id": 1,
                    "status": "completed",
                    "progress_percentage": 100,
                    "collected_items": 200,
                    "total_items": 200,
                },
                "is_complete": True,
                "can_resume": False,
            },
            response_only=True,
        ),
    ],
)


resume_collection_schema = extend_schema(
    summary="Resume a paused or failed collection",
    description=(
        "Resume a collection that was paused or failed. "
        "Collection will continue from the last collected item."
    ),
    tags=["Collection Management"],
    parameters=[
        OpenApiParameter(
            name="plan_id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Collection plan ID",
        ),
    ],
    request=None,
    responses={
        200: OpenApiTypes.OBJECT,
        400: OpenApiTypes.OBJECT,
        401: OpenApiTypes.OBJECT,
        404: OpenApiTypes.OBJECT,
    },
    examples=[
        OpenApiExample(
            "Success Response",
            value={
                "success": True,
                "message": "Collection resumed",
                "last_collected_item": "42",
            },
            response_only=True,
        ),
        OpenApiExample(
            "Error - Cannot Resume",
            value={
                "error": "Collection cannot be resumed. Status must be paused or failed.",
            },
            response_only=True,
        ),
    ],
)


collection_plans_list_schema = extend_schema(
    summary="List all collection plans",
    description="Get all collections for the authenticated user.",
    tags=["Collection Management"],
    responses={
        200: CollectionSerializer(many=True),
        401: OpenApiTypes.OBJECT,
    },
    examples=[
        OpenApiExample(
            "Success Response",
            value=[
                {
                    "id": 1,
                    "repository_name": "my-repo",
                    "status": "completed",
                    "progress_percentage": 100,
                    "created_at": "2025-01-15T10:30:00Z",
                },
                {
                    "id": 2,
                    "repository_name": "another-repo",
                    "status": "in_progress",
                    "progress_percentage": 45,
                    "created_at": "2025-01-20T14:00:00Z",
                },
            ],
            response_only=True,
        ),
    ],
)


collection_history_schema = extend_schema(
    summary="Get collection history for a repository",
    description="Retrieve all collections (past and current) for a specific repository.",
    tags=["Collection Management"],
    parameters=[
        OpenApiParameter(
            name="repository_id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Repository ID",
        ),
    ],
    responses={
        200: OpenApiTypes.OBJECT,
        401: OpenApiTypes.OBJECT,
    },
    examples=[
        OpenApiExample(
            "Success Response",
            value={
                "success": True,
                "collections": [
                    {
                        "id": 1,
                        "status": "completed",
                        "created_at": "2025-01-15T10:30:00Z",
                        "completed_at": "2025-01-15T11:00:00Z",
                    },
                    {
                        "id": 2,
                        "status": "failed",
                        "created_at": "2025-01-20T14:00:00Z",
                        "error_message": "Rate limit exceeded",
                    },
                ],
                "total": 2,
            },
            response_only=True,
        ),
    ],
)


delete_collection_schema = extend_schema(
    summary="Delete a collection",
    description=(
        "Permanently delete a collection and all its related data, "
        "including raw data and cleaned data files from storage."
    ),
    tags=["Collection Management"],
    parameters=[
        OpenApiParameter(
            name="collection_id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Collection ID",
        ),
    ],
    responses={
        200: OpenApiTypes.OBJECT,
        401: OpenApiTypes.OBJECT,
        404: OpenApiTypes.OBJECT,
        500: OpenApiTypes.OBJECT,
    },
    examples=[
        OpenApiExample(
            "Success Response",
            value={
                "success": True,
                "message": "Collection and all related data deleted successfully",
            },
            response_only=True,
        ),
    ],
)


# =============================================================================
# Collected Data Schemas
# =============================================================================

collected_data_schema = extend_schema(
    summary="Get collected data",
    description="Retrieve the collected data for a collection from storage.",
    tags=["Collected Data"],
    parameters=[
        OpenApiParameter(
            name="plan_id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Collection plan ID",
        ),
    ],
    responses={
        200: OpenApiTypes.OBJECT,
        401: OpenApiTypes.OBJECT,
        404: OpenApiTypes.OBJECT,
        500: OpenApiTypes.OBJECT,
    },
    examples=[
        OpenApiExample(
            "Success Response",
            value={
                "found": True,
                "data": {
                    "pull_requests": [
                        {"number": 1, "title": "First PR", "state": "merged"},
                        {"number": 2, "title": "Second PR", "state": "open"},
                    ],
                },
                "stats": {
                    "total_items": 2,
                },
            },
            response_only=True,
        ),
    ],
)


download_collection_json_schema = extend_schema(
    summary="Download collection as JSON",
    description="Download the raw collected data as a JSON file.",
    tags=["Collected Data"],
    parameters=[
        OpenApiParameter(
            name="collection_id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Collection ID",
        ),
    ],
    responses={
        200: OpenApiResponse(
            description="JSON file download",
            response=OpenApiTypes.BINARY,
        ),
        401: OpenApiTypes.OBJECT,
        404: OpenApiTypes.OBJECT,
    },
)


# =============================================================================
# Data Cleaning Schemas
# =============================================================================

data_cleaning_config_schema = extend_schema(
    summary="Get data cleaning configuration",
    description=(
        "Get the current data available for cleaning configuration. "
        "Returns date ranges, available authors, and file extensions found in the data."
    ),
    tags=["Data Cleaning"],
    parameters=[
        OpenApiParameter(
            name="plan_id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Collection plan ID",
        ),
    ],
    responses={
        200: OpenApiTypes.OBJECT,
        400: OpenApiTypes.OBJECT,
        401: OpenApiTypes.OBJECT,
        404: OpenApiTypes.OBJECT,
    },
    examples=[
        OpenApiExample(
            "Success Response",
            value={
                "success": True,
                "date_range": {
                    "min_date": "2024-01-01",
                    "max_date": "2024-12-31",
                },
                "available_authors": ["john.doe", "jane.smith"],
                "file_extensions": [".py", ".js", ".ts"],
                "total_items": 150,
            },
            response_only=True,
        ),
    ],
)


apply_filters_csv_schema = extend_schema(
    summary="Apply filters and create CSV",
    description=(
        "Apply cleaning filters to the collected data and generate structured CSV files. "
        "This creates both a structured data CSV and a statistics CSV."
    ),
    tags=["Data Cleaning"],
    parameters=[
        OpenApiParameter(
            name="plan_id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Collection plan ID",
        ),
    ],
    request=inline_serializer(
        name="ApplyFiltersRequest",
        fields={
            "file_extensions": serializers.ListField(
                child=serializers.CharField(),
                required=False,
                help_text="Filter by file extensions",
            ),
            "authors": serializers.ListField(
                child=serializers.CharField(),
                required=False,
                help_text="Filter by author usernames",
            ),
            "keyword_field": serializers.CharField(
                required=False,
                help_text="Field to search for keywords (e.g., 'title', 'description')",
            ),
            "keywords": serializers.ListField(
                child=serializers.CharField(),
                required=False,
                help_text="Keywords to filter by",
            ),
            "replace_json": serializers.BooleanField(
                required=False,
                default=False,
                help_text="Replace existing filtered data",
            ),
        },
    ),
    responses={
        200: OpenApiTypes.OBJECT,
        401: OpenApiTypes.OBJECT,
        404: OpenApiTypes.OBJECT,
        500: OpenApiTypes.OBJECT,
    },
    examples=[
        OpenApiExample(
            "Request Example",
            value={
                "file_extensions": [".py", ".js"],
                "authors": ["john.doe"],
                "keyword_field": "title",
                "keywords": ["fix", "bug"],
                "replace_json": False,
            },
            request_only=True,
        ),
        OpenApiExample(
            "Success Response",
            value={
                "success": True,
                "message": "Structured CSV created successfully",
                "structured_csv_filename": "collection_1_structured.csv",
                "statistics_csv_filename": "collection_1_statistics.csv",
                "filtered_count": 45,
            },
            response_only=True,
        ),
    ],
)


# =============================================================================
# Cleaned Data Schemas
# =============================================================================

collection_cleaned_data_list_schema = extend_schema(
    summary="List cleaned data for a collection",
    description="Get all cleaned data instances for a specific collection.",
    tags=["Cleaned Data"],
    parameters=[
        OpenApiParameter(
            name="collection_id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Collection ID",
        ),
    ],
    responses={
        200: OpenApiTypes.OBJECT,
        401: OpenApiTypes.OBJECT,
        404: OpenApiTypes.OBJECT,
    },
    examples=[
        OpenApiExample(
            "Success Response",
            value={
                "success": True,
                "cleaned_data": [
                    {
                        "id": 1,
                        "collection_id": 1,
                        "status": "completed",
                        "start_date": "2024-01-01",
                        "end_date": "2024-06-30",
                        "created_at": "2025-01-15T10:30:00Z",
                    },
                    {
                        "id": 2,
                        "collection_id": 1,
                        "status": "completed",
                        "start_date": "2024-07-01",
                        "end_date": "2024-12-31",
                        "created_at": "2025-01-16T14:00:00Z",
                    },
                ],
                "collection": {
                    "id": 1,
                    "repository_name": "my-repo",
                    "status": "completed",
                },
            },
            response_only=True,
        ),
    ],
)


create_cleaned_data_schema = extend_schema(
    summary="Create cleaned data",
    description=(
        "Create a new cleaned data instance with specified filters. "
        "This allows creating multiple filtered views of the same collection."
    ),
    tags=["Cleaned Data"],
    request=CreateCleanedDataSerializer,
    responses={
        201: OpenApiTypes.OBJECT,
        400: OpenApiTypes.OBJECT,
        401: OpenApiTypes.OBJECT,
        404: OpenApiTypes.OBJECT,
        500: OpenApiTypes.OBJECT,
    },
    examples=[
        OpenApiExample(
            "Request Example",
            value={
                "collection_id": 1,
                "start_date": "2024-01-01",
                "end_date": "2024-06-30",
                "filters": {
                    "authors": ["john.doe"],
                    "file_extensions": [".py"],
                },
            },
            request_only=True,
        ),
        OpenApiExample(
            "Success Response",
            value={
                "success": True,
                "message": "Cleaning and Filtering Successful",
                "cleaned_data": {
                    "id": 1,
                    "collection_id": 1,
                    "status": "completed",
                    "start_date": "2024-01-01",
                    "end_date": "2024-06-30",
                    "structured_csv_filename": "cleaned_1_structured.csv",
                    "statistics_csv_filename": "cleaned_1_statistics.csv",
                },
            },
            response_only=True,
        ),
    ],
)


cleaned_data_detail_get_schema = extend_schema(
    summary="Get cleaned data details",
    description="Retrieve details of a specific cleaned data instance.",
    tags=["Cleaned Data"],
    parameters=[
        OpenApiParameter(
            name="cleaned_data_id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Cleaned data ID",
        ),
    ],
    responses={
        200: CleanedDataSerializer,
        401: OpenApiTypes.OBJECT,
        403: OpenApiTypes.OBJECT,
        404: OpenApiTypes.OBJECT,
    },
)


cleaned_data_detail_delete_schema = extend_schema(
    summary="Delete cleaned data",
    description="Delete a specific cleaned data instance and its associated files.",
    tags=["Cleaned Data"],
    parameters=[
        OpenApiParameter(
            name="cleaned_data_id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Cleaned data ID",
        ),
    ],
    responses={
        200: OpenApiTypes.OBJECT,
        401: OpenApiTypes.OBJECT,
        403: OpenApiTypes.OBJECT,
        404: OpenApiTypes.OBJECT,
        500: OpenApiTypes.OBJECT,
    },
    examples=[
        OpenApiExample(
            "Success Response",
            value={
                "success": True,
                "message": "Cleaned data deleted successfully",
            },
            response_only=True,
        ),
    ],
)


download_cleaned_data_csv_schema = extend_schema(
    summary="Download cleaned data CSV",
    description=(
        "Download a CSV file from a cleaned data instance. "
        "File type can be 'structured' for the main data or 'statistics' for aggregated stats."
    ),
    tags=["Cleaned Data"],
    parameters=[
        OpenApiParameter(
            name="cleaned_data_id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Cleaned data ID",
        ),
        OpenApiParameter(
            name="file_type",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.PATH,
            description="Type of CSV file to download",
            enum=["structured", "statistics"],
        ),
    ],
    responses={
        200: OpenApiResponse(
            description="CSV file download",
            response=OpenApiTypes.BINARY,
        ),
        400: OpenApiTypes.OBJECT,
        401: OpenApiTypes.OBJECT,
        403: OpenApiTypes.OBJECT,
        404: OpenApiTypes.OBJECT,
    },
)
