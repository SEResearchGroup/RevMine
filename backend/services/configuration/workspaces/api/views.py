from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.core.paginator import Paginator

from workspaces.models import Workspace, Repository
from workspaces.api.serializers import (
    WorkspaceSerializer,
    WorkspaceListSerializer,
    TestConnectionSerializer,
    RepositorySerializer,
)
from workspaces.services.workspace_service import WorkspaceService
from workspaces.services.repository_service import RepositoryService
from workspaces.infrastructure.git.connection_service import ConnectionService
from workspaces.api.schema import (
    workspace_list_schema,
    workspace_create_schema,
    workspace_detail_retrieve_schema,
    workspace_update_put_schema,
    workspace_update_patch_schema,
    workspace_delete_schema,
    workspace_token_schema,
    workspace_test_connection_schema,
    workspace_repositories_schema,
    repository_import_schema,
    repository_list_schema,
    repository_detail_schema,
    repository_delete_schema,
)


class WorkspaceListCreateView(APIView):
    """List and creation of workspaces."""

    @workspace_list_schema
    def get(self, request):
        """List all workspaces of the user with optional pagination and filtering."""
        if not request.user_id:
            return Response(
                {"error": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        queryset = Workspace.objects.filter(user=request.user_id)

        platform = request.query_params.get("platform")
        if platform:
            queryset = queryset.filter(platform=platform)

        date_from = request.query_params.get("date_from")
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)

        date_to = request.query_params.get("date_to")
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)

        search = request.query_params.get("search")
        if search:
            queryset = queryset.filter(name__icontains=search)

        total = queryset.count()

        page_size = int(request.query_params.get("page_size", 20))
        page = int(request.query_params.get("page", 1))
        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page)

        serializer = WorkspaceListSerializer(page_obj.object_list, many=True)
        return Response(
            {
                "results": serializer.data,
                "total": total,
                "page": page,
                "page_size": page_size,
                "num_pages": paginator.num_pages,
                "has_next": page_obj.has_next(),
            }
        )

    @workspace_create_schema
    def post(self, request):
        """Create a workspace after validating the connection."""
        if not request.user_id:
            return Response(
                {"error": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        serializer = WorkspaceSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            workspace, connection_result = WorkspaceService.create_workspace(
                request.user_id, serializer.validated_data
            )
            return Response(
                {
                    "workspace": WorkspaceSerializer(workspace).data,
                    "connection_test": connection_result,
                },
                status=status.HTTP_201_CREATED,
            )
        except ValueError as e:
            return Response(
                {"error": "Connection test failed", "message": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class WorkspaceDetailView(APIView):
    """Retrieve, update, and delete a specific workspace."""

    def _get_workspace(self, request, workspace_id):
        return get_object_or_404(Workspace, id=workspace_id, user=request.user_id)

    def _check_auth(self, request):
        if not request.user_id:
            return Response(
                {"error": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        return None

    @workspace_detail_retrieve_schema
    def get(self, request, workspace_id):
        """Retrieve details of a specific workspace."""
        auth_error = self._check_auth(request)
        if auth_error:
            return auth_error
        workspace = self._get_workspace(request, workspace_id)
        return Response(WorkspaceSerializer(workspace).data)

    @workspace_update_put_schema
    def put(self, request, workspace_id):
        """Full update of the workspace."""
        return self._update(request, workspace_id, partial=False)

    @workspace_update_patch_schema
    def patch(self, request, workspace_id):
        """Partial update of the workspace."""
        return self._update(request, workspace_id, partial=True)

    def _update(self, request, workspace_id, partial=False):
        auth_error = self._check_auth(request)
        if auth_error:
            return auth_error

        workspace = self._get_workspace(request, workspace_id)
        serializer = WorkspaceSerializer(workspace, data=request.data, partial=partial)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        token = serializer.validated_data.pop("token", None)

        try:
            workspace = WorkspaceService.update_workspace(
                workspace, serializer.validated_data, token
            )
            return Response(WorkspaceSerializer(workspace).data)
        except ValueError as e:
            return Response(
                {"error": "Connection test failed", "message": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @workspace_delete_schema
    def delete(self, request, workspace_id):
        """Delete a workspace."""
        auth_error = self._check_auth(request)
        if auth_error:
            return auth_error
        workspace = self._get_workspace(request, workspace_id)
        workspace.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class WorkspaceTokenView(APIView):
    """Retrieve the token of a workspace (internal use)."""

    @workspace_token_schema
    def get(self, request, workspace_id):
        """Retrieve the token of the workspace."""
        if not request.user_id:
            return Response(
                {"error": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        workspace = get_object_or_404(Workspace, id=workspace_id, user=request.user_id)
        return Response(
            {
                "token": workspace.get_token(),
                "platform": workspace.platform,
                "url": workspace.url,
            }
        )


class WorkspaceTestConnectionView(APIView):
    """Test connection to a Git API."""

    @workspace_test_connection_schema
    def post(self, request, workspace_id=None):
        """Test a connection (existing workspace or new credentials)."""
        if not request.user_id:
            return Response(
                {"error": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if workspace_id:
            workspace = get_object_or_404(
                Workspace, id=workspace_id, user=request.user_id
            )
            token = workspace.get_token()
            platform = workspace.platform
            url = workspace.url
        else:
            serializer = TestConnectionSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            platform = serializer.validated_data["platform"]
            token = serializer.validated_data["token"]
            url = serializer.validated_data.get("url")

        result = ConnectionService.test_connection(platform, token, url)
        response_status = (
            status.HTTP_200_OK if result["success"] else status.HTTP_400_BAD_REQUEST
        )
        return Response(result, status=response_status)


class WorkspaceRepositoriesView(APIView):
    """Fetch repositories from the Git API for a workspace."""

    @workspace_repositories_schema
    def get(self, request, workspace_id):
        """Fetch repositories from the Git API."""
        if not request.user_id:
            return Response(
                {"error": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        workspace = get_object_or_404(Workspace, id=workspace_id, user=request.user_id)

        if not workspace.is_active:
            return Response(
                {"error": "Workspace is not active"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = RepositoryService.fetch_repositories(
            workspace.platform, workspace.get_token(), workspace.url
        )

        if result["success"]:
            return Response(
                {
                    "workspace_id": workspace.id,
                    "workspace_name": workspace.name,
                    "platform": workspace.platform,
                    "repositories": result["repositories"],
                    "total": len(result["repositories"]),
                    "message": result["message"],
                },
                status=status.HTTP_200_OK,
            )
        return Response(
            {"error": "Failed to fetch repositories", "message": result["message"]},
            status=status.HTTP_400_BAD_REQUEST,
        )


class RepositoryImportView(APIView):
    """Import selected repositories."""

    @repository_import_schema
    def post(self, request, workspace_id):
        """Import selected repositories into the database."""
        workspace = get_object_or_404(Workspace, id=workspace_id)
        repository_ids = request.data.get("repository_ids", [])

        if not repository_ids:
            return Response(
                {"error": "No repository selected"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            imported_repos, errors = RepositoryService.import_repositories(
                workspace, repository_ids
            )
            imported_count = len(imported_repos)
            response_status = status.HTTP_201_CREATED
            if errors and imported_count == 0:
                response_status = status.HTTP_400_BAD_REQUEST
            elif errors:
                response_status = status.HTTP_207_MULTI_STATUS

            return Response(
                {
                    "success": not errors,
                    "imported_count": imported_count,
                    "repositories": RepositorySerializer(
                        imported_repos, many=True
                    ).data,
                    "errors": errors,
                    "message": (
                        f"{imported_count} repositories imported, {len(errors)} failed"
                        if errors
                        else f"{imported_count} repositories imported successfully"
                    ),
                },
                status=response_status,
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(
                {"error": f"Import error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class RepositoryListView(APIView):
    """List imported repositories for a workspace."""

    @repository_list_schema
    def get(self, request, workspace_id):
        """List all imported repositories with optional filtering."""
        if not request.user_id:
            return Response(
                {"error": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        queryset = Repository.objects.filter(
            workspace_id=workspace_id,
            workspace__user=request.user_id,
        )

        is_active = request.query_params.get("is_active")
        if is_active is not None:
            if is_active.lower() in ("true", "1"):
                queryset = queryset.filter(is_active=True)
            elif is_active.lower() in ("false", "0"):
                queryset = queryset.filter(is_active=False)

        search = request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(full_name__icontains=search)
            )

        return Response(RepositorySerializer(queryset, many=True).data)


class RepositoryDetailView(APIView):
    """Detailed operations on a repository."""

    def _get_repository(self, request, workspace_id, repository_id):
        return get_object_or_404(
            Repository,
            id=repository_id,
            workspace_id=workspace_id,
            workspace__user=request.user_id,
        )

    @repository_detail_schema
    def get(self, request, workspace_id, repository_id):
        """Retrieve the details of a repository."""
        if not request.user_id:
            return Response(
                {"error": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        repository = self._get_repository(request, workspace_id, repository_id)
        return Response(RepositorySerializer(repository).data)

    @repository_detail_schema
    def patch(self, request, workspace_id, repository_id):
        """Update allowed fields of a repository (is_active, description)."""
        if not request.user_id:
            return Response(
                {"error": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        repository = self._get_repository(request, workspace_id, repository_id)
        allowed_fields = ["is_active", "description"]
        for key, value in request.data.items():
            if key in allowed_fields:
                setattr(repository, key, value)
        repository.save()
        return Response(RepositorySerializer(repository).data)

    @repository_delete_schema
    def delete(self, request, workspace_id, repository_id):
        """Delete a repository."""
        if not request.user_id:
            return Response(
                {"error": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        repository = self._get_repository(request, workspace_id, repository_id)
        repository.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AllRepositoriesView(APIView):
    """List all repositories across all workspaces for the authenticated user."""

    def get(self, request):
        if not request.user_id:
            return Response(
                {"error": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        queryset = Repository.objects.filter(
            workspace__user=request.user_id
        ).select_related("workspace")

        platform = request.query_params.get("platform")
        if platform:
            queryset = queryset.filter(workspace__platform=platform)

        workspace_id = request.query_params.get("workspace_id")
        if workspace_id:
            queryset = queryset.filter(workspace_id=workspace_id)

        search = request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(full_name__icontains=search)
            )

        total = queryset.count()
        page_size = int(request.query_params.get("page_size", 20))
        page = int(request.query_params.get("page", 1))
        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page)

        serializer = RepositorySerializer(page_obj.object_list, many=True)
        return Response(
            {
                "results": serializer.data,
                "total": total,
                "page": page,
                "page_size": page_size,
                "num_pages": paginator.num_pages,
                "has_next": page_obj.has_next(),
            }
        )
