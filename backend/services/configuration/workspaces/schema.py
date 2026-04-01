# schema.py
from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter,
    OpenApiExample,
)
from drf_spectacular.types import OpenApiTypes

from .serializers import (
    WorkspaceSerializer,
    WorkspaceListSerializer,
    TestConnectionSerializer,
    RepositorySerializer,
)

# ---------- Workspace list & create ----------

workspace_list_schema = extend_schema(
    summary="List all workspaces",
    description="Retrieve all workspaces belonging to the authenticated user.",
    tags=["Workspaces"],
    responses={
        200: WorkspaceListSerializer(many=True),
        401: OpenApiTypes.OBJECT,
    },
    examples=[
        OpenApiExample(
            "Success Response",
            value={
                "id": 1,
                "name": "My GitHub Workspace",
                "platform": "github",
                "is_active": True,
                "created_at": "2025-01-15T10:30:00Z",
            },
            response_only=True,
        ),
    ],
)

workspace_create_schema = extend_schema(
    summary="Create a new workspace",
    description="Create a new Git workspace after validating the connection.",
    tags=["Workspaces"],
    request=WorkspaceSerializer,
    responses={
        201: OpenApiTypes.OBJECT,
        400: OpenApiTypes.OBJECT,
        401: OpenApiTypes.OBJECT,
    },
    examples=[
        OpenApiExample(
            "GitHub Workspace",
            value={
                "name": "My GitHub Workspace",
                "description": "Main development workspace",
                "platform": "github",
                "token": "ghp_xxxxxxxxxxxxxxxxxxxx",
            },
            request_only=True,
        ),
        OpenApiExample(
            "GitLab Self-hosted",
            value={
                "name": "Company GitLab",
                "platform": "gitlabself",
                "url": "https://gitlab.company.com",
                "token": "glpat-xxxxxxxxxxxxxxxxxxxx",
            },
            request_only=True,
        ),
        OpenApiExample(
            "Success Response",
            value={
                "workspace": {
                    "id": 1,
                    "name": "My GitHub Workspace",
                    "platform": "github",
                    "is_active": True,
                },
                "connection_test": {
                    "success": True,
                    "message": "Connection successful",
                    "user_data": {"login": "username"},
                },
            },
            response_only=True,
        ),
    ],
)

# ---------- Workspace detail (retrieve / update / delete) ----------

workspace_detail_retrieve_schema = extend_schema(
    summary="Get workspace details",
    description="Retrieve detailed information about a specific workspace.",
    tags=["Workspaces"],
    parameters=[
        OpenApiParameter(
            name="workspace_id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Workspace ID",
        ),
    ],
    responses={
        200: WorkspaceSerializer,
        401: OpenApiTypes.OBJECT,
        404: OpenApiTypes.OBJECT,
    },
)

workspace_update_put_schema = extend_schema(
    summary="Update workspace (full)",
    description=(
        "Completely update a workspace with connection validation if the token changes."
    ),
    tags=["Workspaces"],
    request=WorkspaceSerializer,
    parameters=[
        OpenApiParameter(
            name="workspace_id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Workspace ID",
        ),
    ],
    responses={
        200: WorkspaceSerializer,
        400: OpenApiTypes.OBJECT,
        401: OpenApiTypes.OBJECT,
        404: OpenApiTypes.OBJECT,
    },
)

workspace_update_patch_schema = extend_schema(
    summary="Update workspace (partial)",
    description=(
        "Partially update a workspace with connection validation if the token changes."
    ),
    tags=["Workspaces"],
    request=WorkspaceSerializer,
    parameters=[
        OpenApiParameter(
            name="workspace_id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Workspace ID",
        ),
    ],
    responses={
        200: WorkspaceSerializer,
        400: OpenApiTypes.OBJECT,
        401: OpenApiTypes.OBJECT,
        404: OpenApiTypes.OBJECT,
    },
)

workspace_delete_schema = extend_schema(
    summary="Delete workspace",
    description="Permanently delete a workspace.",
    tags=["Workspaces"],
    parameters=[
        OpenApiParameter(
            name="workspace_id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Workspace ID",
        ),
    ],
    responses={
        204: None,
        401: OpenApiTypes.OBJECT,
        404: OpenApiTypes.OBJECT,
    },
)

# ---------- Workspace token (internal) ----------

workspace_token_schema = extend_schema(
    summary="Get workspace token (internal)",
    description="Retrieve decrypted workspace token for inter-service use.",
    tags=["Workspaces - Internal"],
    parameters=[
        OpenApiParameter(
            name="workspace_id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Workspace ID",
        ),
    ],
    responses={
        200: OpenApiTypes.OBJECT,
        401: OpenApiTypes.OBJECT,
        404: OpenApiTypes.OBJECT,
    },
)

# ---------- Test connection ----------

workspace_test_connection_schema = extend_schema(
    summary="Test connection",
    description=(
        "Test a Git API connection without saving for a new workspace "
        "or test an existing workspace connection."
    ),
    tags=["Connection Testing"],
    request=TestConnectionSerializer,
    parameters=[
        OpenApiParameter(
            name="workspace_id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Workspace ID (optional, for testing existing workspace)",
            required=False,
        ),
    ],
    responses={
        200: OpenApiTypes.OBJECT,
        400: OpenApiTypes.OBJECT,
        401: OpenApiTypes.OBJECT,
    },
    examples=[
        OpenApiExample(
            "Test GitHub Connection",
            value={
                "platform": "github",
                "token": "ghp_xxxxxxxxxxxxxxxxxxxx",
            },
            request_only=True,
        ),
        OpenApiExample(
            "Success Response",
            value={
                "success": True,
                "message": "Connection successful",
                "user_data": {
                    "login": "username",
                    "name": "John Doe",
                    "email": "john@example.com",
                },
            },
            response_only=True,
        ),
        OpenApiExample(
            "Error Response",
            value={
                "success": False,
                "message": "Invalid or expired token",
            },
            response_only=True,
        ),
    ],
)

# ---------- Workspace repositories (list from platform) ----------

workspace_repositories_schema = extend_schema(
    summary="List workspace repositories",
    description="Fetch all repositories accessible through the workspace Git platform.",
    tags=["Repositories"],
    parameters=[
        OpenApiParameter(
            name="workspace_id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Workspace ID",
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
                "workspace_id": 1,
                "workspace_name": "My GitHub Workspace",
                "platform": "github",
                "total": 2,
                "message": "2 repositories found",
                "repositories": [
                    {
                        "id": 123456,
                        "name": "my-project",
                        "full_name": "username/my-project",
                        "description": "Project description",
                        "url": "https://github.com/username/my-project",
                        "clone_url": "https://github.com/username/my-project.git",
                        "ssh_url": "git@github.com:username/my-project.git",
                        "default_branch": "main",
                        "private": False,
                        "language": "Python",
                        "updated_at": "2025-01-15T10:30:00Z",
                        "visibility": "public",
                    }
                ],
            },
            response_only=True,
        ),
    ],
)

# ---------- Import repositories ----------

repository_import_schema = extend_schema(
    summary="Import selected repositories",
    description=(
        "Import the selected Git repositories into the database using their external IDs."
    ),
    tags=["Repositories"],
    parameters=[
        OpenApiParameter(
            name="workspace_id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="ID of the workspace to import repositories into",
        ),
    ],
    request={
        "application/json": {
            "type": "object",
            "properties": {
                "repository_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of external IDs (GitHub/GitLab) of the repositories to import",
                }
            },
            "required": ["repository_ids"],
            "example": {"repository_ids": ["123456789", "987654321"]},
        }
    },
    responses={
        201: OpenApiTypes.OBJECT,
        400: OpenApiTypes.OBJECT,
        404: OpenApiTypes.OBJECT,
        500: OpenApiTypes.OBJECT,
    },
    examples=[
        OpenApiExample(
            name="Valid request",
            value={"repository_ids": ["123456789", "987654321"]},
            request_only=True,
        ),
        OpenApiExample(
            name="Success response",
            value={
                "success": True,
                "imported_count": 2,
                "repositories": [
                    {
                        "id": 5,
                        "workspace": 1,
                        "external_id": "123456789",
                        "name": "my-project",
                        "full_name": "user/my-project",
                        "is_active": True,
                        "imported_at": "2025-11-25T20:00:00Z",
                    }
                ],
                "errors": [],
            },
            response_only=True,
        ),
        OpenApiExample(
            name="Partial error",
            value={
                "success": True,
                "imported_count": 1,
                "repositories": [
                    {
                        "id": 1,
                        "workspace": 2,
                        "workspace_name": "My workspace",
                        "platform": "github",
                        "external_id": "1122",
                        "name": "dashboard",
                        "full_name": "abcd/dashboard",
                        "description": "Dashboard project",
                        "url": "https://api.github.com/repos/abcd/dashboard",
                        "web_url": "https://github.com/abcd/dashboard",
                        "owner": "abcd",
                        "owner_type": "User",
                        "default_branch": "main",
                        "language": "JavaScript",
                        "stars_count": 0,
                        "forks_count": 0,
                        "open_issues_count": 0,
                        "is_private": True,
                        "is_fork": False,
                        "is_archived": False,
                        "is_active": True,
                        "created_at_platform": "2022-09-11T20:21:51Z",
                        "last_activity_at": "2025-11-23T17:37:08Z",
                        "last_analyzed_at": None,
                        "imported_at": "2025-11-25T19:23:42.871826Z",
                        "updated_at": "2025-11-25T19:23:42.871834Z",
                    }
                ],
                "errors": [
                    {
                        "repository": "unknown-repo",
                        "error": "Repository not found or inaccessible",
                    }
                ],
            },
            response_only=True,
        ),
    ],
)

# ---------- Repository list / detail / update / delete ----------

repository_list_schema = extend_schema(
    summary="List imported repositories of a workspace",
    description=(
        "Return the list of repositories already imported into a workspace, "
        "with optional filters."
    ),
    tags=["Repositories"],
    parameters=[
        OpenApiParameter(
            name="workspace_id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Workspace ID",
            required=True,
        ),
        OpenApiParameter(
            name="is_active",
            type=OpenApiTypes.BOOL,
            location=OpenApiParameter.QUERY,
            description="Filter by active state (true/false)",
            required=False,
        ),
        OpenApiParameter(
            name="search",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description="Text search in name or full_name",
            required=False,
        ),
    ],
    responses={
        200: RepositorySerializer(many=True),
    },
    examples=[
        OpenApiExample(
            name="Example response",
            value={
                "id": 3,
                "workspace": 1,
                "workspace_name": "My GitHub Workspace",
                "platform": "github",
                "external_id": "112233445",
                "name": "api-service",
                "full_name": "company/api-service",
                "description": "Main API service",
                "web_url": "https://github.com/company/api-service",
                "default_branch": "main",
                "language": "Python",
                "is_private": True,
                "is_active": True,
                "imported_at": "2025-11-20T14:30:22Z",
                "last_activity_at": "2025-11-24T09:15:00Z",
            },
            response_only=True,
        )
    ],
)

repository_detail_schema = extend_schema(
    summary="Detail of an imported repository",
    description="Retrieve all information about a previously imported repository.",
    tags=["Repositories"],
    parameters=[
        OpenApiParameter(
            name="repository_id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Internal ID of the repository in the application",
            required=True,
        ),
    ],
    responses={
        200: RepositorySerializer,
    },
    examples=[
        OpenApiExample(
            name="Detailed repository",
            value={
                "id": 7,
                "workspace": 2,
                "workspace_name": "company GitLab",
                "platform": "gitlabself",
                "external_id": "4455",
                "name": "frontend-app",
                "full_name": "frontend/frontend-app",
                "description": "Main React application",
                "web_url": "https://gitlab.company.com/frontend/frontend-app",
                "default_branch": "master",
                "language": None,
                "is_private": True,
                "is_active": True,
                "is_fork": False,
                "is_archived": False,
                "created_at_platform": "2023-06-15T08:22:11Z",
                "last_activity_at": "2025-11-25T12:04:33Z",
                "imported_at": "2025-11-01T10:15:44Z",
            },
            response_only=True,
        )
    ],
)

repository_partial_update_schema = extend_schema(
    summary="Update an imported repository",
    description=(
        "Partial update allowed only on the fields `is_active` and `description`."
    ),
    tags=["Repositories"],
    parameters=[
        OpenApiParameter(
            name="repository_id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            required=True,
            description="Repository ID",
        ),
    ],
    request=OpenApiTypes.OBJECT,
    responses={
        200: RepositorySerializer,
    },
    examples=[
        OpenApiExample(
            name="Example PATCH",
            value={
                "is_active": False,
                "description": "Project temporarily archived",
            },
            request_only=True,
        )
    ],
)

repository_delete_schema = extend_schema(
    summary="Delete an imported repository",
    description=(
        "Permanently delete a repository from the database. "
        "This does not affect the remote repository."
    ),
    tags=["Repositories"],
    parameters=[
        OpenApiParameter(
            name="repository_id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            required=True,
            description="Repository ID",
        ),
    ],
    responses={
        204: None,
    },
)
