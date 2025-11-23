from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes
import requests
from .models import Workspace
from .serializers import WorkspaceSerializer, WorkspaceListSerializer, TestConnectionSerializer


class WorkspaceConnectionTester:
    """Service for testing Git API connections"""
    
    @staticmethod
    def test_connection(platform: str, token: str, url: str = None) -> dict:
        """
        Test connection to Git API
        Returns: {'success': bool, 'message': str, 'user_data': dict}
        """
        try:
            if platform == 'github':
                api_url = 'https://api.github.com'
                headers = {'Authorization': f'token {token}'}
            elif platform == 'gitlab':
                api_url = 'https://gitlab.com/api/v4'
                headers = {'PRIVATE-TOKEN': token}
            else:  # gitlab_self
                if not url:
                    return {'success': False, 'message': 'URL required for GitLab self-hosted'}
                api_url = url.rstrip('/') + '/api/v4'
                headers = {'PRIVATE-TOKEN': token}

            resp = requests.get(
                f'{api_url}/user',
                headers=headers,
                timeout=10
            )

            if resp.status_code == 200:
                return {
                    'success': True,
                    'message': 'Connection successful',
                    'user_data': resp.json()
                }
            elif resp.status_code == 401:
                return {'success': False, 'message': 'Invalid or expired token'}
            else:
                return {'success': False, 'message': f'API error: {resp.status_code}'}

        except requests.Timeout:
            return {'success': False, 'message': 'Timeout: server not responding'}
        except requests.RequestException as e:
            return {'success': False, 'message': f'Connection error: {str(e)}'}


class RepositoryFetcher:
    """Service for fetching repositories from Git APIs"""
    
    @staticmethod
    def fetch_repositories(platform: str, token: str, url: str = None) -> dict:
        """
        Fetch list of accessible repositories
        Returns: {'success': bool, 'repositories': list, 'message': str}
        """
        try:
            if platform == 'github':
                api_url = 'https://api.github.com'
                headers = {'Authorization': f'token {token}'}
                endpoint = f'{api_url}/user/repos'
                params = {
                    'per_page': 100,
                    'sort': 'updated',
                    'affiliation': 'owner,collaborator,organization_member'
                }
            elif platform == 'gitlab':
                api_url = 'https://gitlab.com/api/v4'
                headers = {'PRIVATE-TOKEN': token}
                endpoint = f'{api_url}/projects'
                params = {
                    'per_page': 100,
                    'order_by': 'updated_at',
                    'membership': True
                }
            else:  # gitlab_self
                if not url:
                    return {'success': False, 'message': 'URL required for GitLab self-hosted', 'repositories': []}
                api_url = url.rstrip('/') + '/api/v4'
                headers = {'PRIVATE-TOKEN': token}
                endpoint = f'{api_url}/projects'
                params = {
                    'per_page': 100,
                    'order_by': 'updated_at',
                    'membership': True
                }

            resp = requests.get(
                endpoint,
                headers=headers,
                params=params,
                timeout=15
            )

            if resp.status_code == 200:
                repos_data = resp.json()
                repositories = RepositoryFetcher._normalize_repositories(repos_data, platform)
                return {
                    'success': True,
                    'message': f'{len(repositories)} repositories found',
                    'repositories': repositories
                }
            elif resp.status_code == 401:
                return {'success': False, 'message': 'Invalid or expired token', 'repositories': []}
            else:
                return {'success': False, 'message': f'API error: {resp.status_code}', 'repositories': []}

        except requests.Timeout:
            return {'success': False, 'message': 'Timeout: server not responding', 'repositories': []}
        except requests.RequestException as e:
            return {'success': False, 'message': f'Connection error: {str(e)}', 'repositories': []}
    
    @staticmethod
    def _normalize_repositories(repos_data: list, platform: str) -> list:
        """Normalize repository data according to platform"""
        normalized = []
        
        for repo in repos_data:
            if platform == 'github':
                normalized.append({
                    'id': repo.get('id'),
                    'name': repo.get('name'),
                    'full_name': repo.get('full_name'),
                    'description': repo.get('description'),
                    'url': repo.get('html_url'),
                    'clone_url': repo.get('clone_url'),
                    'ssh_url': repo.get('ssh_url'),
                    'default_branch': repo.get('default_branch', 'main'),
                    'private': repo.get('private', False),
                    'language': repo.get('language'),
                    'updated_at': repo.get('updated_at'),
                    'visibility': 'private' if repo.get('private') else 'public'
                })
            else:  # gitlab or gitlab_self
                normalized.append({
                    'id': repo.get('id'),
                    'name': repo.get('name'),
                    'full_name': repo.get('path_with_namespace'),
                    'description': repo.get('description'),
                    'url': repo.get('web_url'),
                    'clone_url': repo.get('http_url_to_repo'),
                    'ssh_url': repo.get('ssh_url_to_repo'),
                    'default_branch': repo.get('default_branch', 'main'),
                    'private': repo.get('visibility') in ['private', 'internal'],
                    'language': None,  
                    'updated_at': repo.get('last_activity_at'),
                    'visibility': repo.get('visibility', 'private')
                })
        
        return normalized


class WorkspaceListCreateView(APIView):
    """
    Workspace management endpoints for listing and creating workspaces
    """
    
    @extend_schema(
        summary="List all workspaces",
        description="Retrieve all workspaces belonging to the authenticated user",
        tags=["Workspaces"],
        responses={
            200: WorkspaceListSerializer(many=True),
            401: OpenApiTypes.OBJECT,
        },
        examples=[
            OpenApiExample(
                'Success Response',
                value=[
                    {
                        "id": 1,
                        "name": "My GitHub Workspace",
                        "platform": "github",
                        "is_active": True,
                        "created_at": "2025-01-15T10:30:00Z"
                    }
                ],
                response_only=True,
            ),
        ]
    )
    def get(self, request):
        """List all workspaces for the authenticated user"""
        if not request.user_id:
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        workspaces = Workspace.objects.filter(user=request.user_id)
        serializer = WorkspaceListSerializer(workspaces, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        summary="Create a new workspace",
        description="Create a new Git workspace after validating the connection",
        tags=["Workspaces"],
        request=WorkspaceSerializer,
        responses={
            201: OpenApiTypes.OBJECT,
            400: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
        },
        examples=[
            OpenApiExample(
                'GitHub Workspace',
                value={
                    "name": "My GitHub Workspace",
                    "description": "Main development workspace",
                    "platform": "github",
                    "token": "ghp_xxxxxxxxxxxxxxxxxxxx"
                },
                request_only=True,
            ),
            OpenApiExample(
                'GitLab Self-hosted',
                value={
                    "name": "Company GitLab",
                    "platform": "gitlab_self",
                    "url": "https://gitlab.company.com",
                    "token": "glpat-xxxxxxxxxxxxxxxxxxxx"
                },
                request_only=True,
            ),
            OpenApiExample(
                'Success Response',
                value={
                    "workspace": {
                        "id": 1,
                        "name": "My GitHub Workspace",
                        "platform": "github",
                        "is_active": True
                    },
                    "connection_test": {
                        "success": True,
                        "message": "Connection successful",
                        "user_data": {"login": "username"}
                    }
                },
                response_only=True,
            ),
        ]
    )
    def post(self, request):
        """Create a workspace after connection validation"""
        if not request.user_id:
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        serializer = WorkspaceSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)        
        
        platform = serializer.validated_data['platform']
        token = serializer.validated_data.pop('token')
        url = serializer.validated_data.get('url')
        
        # Test connection BEFORE saving
        connection_result = WorkspaceConnectionTester.test_connection(platform, token, url)
        
        if not connection_result['success']:
            return Response(
                {
                    'error': 'Connection test failed',
                    'message': connection_result['message']
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # If connection is OK, save workspace
        workspace = Workspace(user=request.user_id, **serializer.validated_data)
        workspace.set_token(token)
        workspace.save()
        
        return Response(
            {
                'workspace': WorkspaceSerializer(workspace).data,
                'connection_test': connection_result
            },
            status=status.HTTP_201_CREATED
        )


class WorkspaceDetailView(APIView):
    """
    Detailed workspace operations (retrieve, update, delete)
    """
    
    def get_object(self, request, workspace_id):
        """Retrieve workspace if user is the owner"""
        workspace = get_object_or_404(Workspace, id=workspace_id, user=request.user_id)
        return workspace
    
    @extend_schema(
        summary="Get workspace details",
        description="Retrieve detailed information about a specific workspace",
        tags=["Workspaces"],
        parameters=[
            OpenApiParameter(
                name='workspace_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description='Workspace ID'
            ),
        ],
        responses={
            200: WorkspaceSerializer,
            401: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        }
    )
    def get(self, request, workspace_id):
        """Retrieve workspace details"""
        if not request.user_id:
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        workspace = self.get_object(request, workspace_id)
        serializer = WorkspaceSerializer(workspace)
        return Response(serializer.data)
    
    @extend_schema(
        summary="Update workspace (full)",
        description="Completely update a workspace with connection validation if token changes",
        tags=["Workspaces"],
        request=WorkspaceSerializer,
        parameters=[
            OpenApiParameter(
                name='workspace_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description='Workspace ID'
            ),
        ],
        responses={
            200: WorkspaceSerializer,
            400: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        }
    )
    def put(self, request, workspace_id):
        """Full workspace update"""
        return self._update(request, workspace_id, partial=False)
    
    @extend_schema(
        summary="Update workspace (partial)",
        description="Partially update a workspace with connection validation if token changes",
        tags=["Workspaces"],
        request=WorkspaceSerializer,
        parameters=[
            OpenApiParameter(
                name='workspace_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description='Workspace ID'
            ),
        ],
        responses={
            200: WorkspaceSerializer,
            400: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        }
    )
    def patch(self, request, workspace_id):
        """Partial workspace update"""
        return self._update(request, workspace_id, partial=True)
    
    def _update(self, request, workspace_id, partial=False):
        """Common logic for PUT and PATCH"""
        if not request.user_id:
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        workspace = self.get_object(request, workspace_id)
        serializer = WorkspaceSerializer(workspace, data=request.data, partial=partial)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # If token is modified, test the connection
        token = serializer.validated_data.pop('token', None)
        
        if token is not None:
            platform = serializer.validated_data.get('platform', workspace.platform)
            url = serializer.validated_data.get('url', workspace.url)
            
            connection_result = WorkspaceConnectionTester.test_connection(platform, token, url)
            
            if not connection_result['success']:
                return Response(
                    {
                        'error': 'Connection test failed',
                        'message': connection_result['message']
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Save modifications
        workspace = serializer.save()
        
        if token is not None:
            workspace.set_token(token)
            workspace.save()
        
        return Response(WorkspaceSerializer(workspace).data)
    
    @extend_schema(
        summary="Delete workspace",
        description="Permanently delete a workspace",
        tags=["Workspaces"],
        parameters=[
            OpenApiParameter(
                name='workspace_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description='Workspace ID'
            ),
        ],
        responses={
            204: None,
            401: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        }
    )
    def delete(self, request, workspace_id):
        """Delete a workspace"""
        if not request.user_id:
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        workspace = self.get_object(request, workspace_id)
        workspace.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class WorkspaceTestConnectionView(APIView):
    """
    Connection testing endpoints
    """
    
    @extend_schema(
        summary="Test connection",
        description="Test a Git API connection without saving (for new workspace) or test existing workspace connection",
        tags=["Connection Testing"],
        request=TestConnectionSerializer,
        parameters=[
            OpenApiParameter(
                name='workspace_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description='Workspace ID (optional, for testing existing workspace)',
                required=False
            ),
        ],
        responses={
            200: OpenApiTypes.OBJECT,
            400: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
        },
        examples=[
            OpenApiExample(
                'Test GitHub Connection',
                value={
                    "platform": "github",
                    "token": "ghp_xxxxxxxxxxxxxxxxxxxx"
                },
                request_only=True,
            ),
            OpenApiExample(
                'Success Response',
                value={
                    "success": True,
                    "message": "Connection successful",
                    "user_data": {
                        "login": "username",
                        "name": "John Doe",
                        "email": "john@example.com"
                    }
                },
                response_only=True,
            ),
            OpenApiExample(
                'Error Response',
                value={
                    "success": False,
                    "message": "Invalid or expired token"
                },
                response_only=True,
            ),
        ]
    )
    def post(self, request, workspace_id=None):
        """Test a connection (existing or new)"""
        if not request.user_id:
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Test existing workspace
        if workspace_id:
            workspace = get_object_or_404(Workspace, id=workspace_id, user=request.user_id)
            token = workspace.get_token()
            platform = workspace.platform
            url = workspace.url
        # Test before creation
        else:
            serializer = TestConnectionSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            platform = serializer.validated_data['platform']
            token = serializer.validated_data['token']
            url = serializer.validated_data.get('url')
        
        result = WorkspaceConnectionTester.test_connection(platform, token, url)
        
        if result['success']:
            return Response(result, status=status.HTTP_200_OK)
        else:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)


class WorkspaceRepositoriesView(APIView):
    """
    Repository management for workspaces
    """
    
    @extend_schema(
        summary="List workspace repositories",
        description="Fetch all repositories accessible through the workspace's Git platform",
        tags=["Repositories"],
        parameters=[
            OpenApiParameter(
                name='workspace_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description='Workspace ID'
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
                'Success Response',
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
                            "visibility": "public"
                        }
                    ]
                },
                response_only=True,
            ),
        ]
    )
    def get(self, request, workspace_id):
        """Retrieve list of workspace repositories"""
        if not request.user_id:
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        workspace = get_object_or_404(Workspace, id=workspace_id, user=request.user_id)
        
        # Check if workspace is active
        if not workspace.is_active:
            return Response(
                {'error': 'Workspace is not active'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Retrieve token and information
        token = workspace.get_token()
        platform = workspace.platform
        url = workspace.url
        
        # Fetch repositories
        result = RepositoryFetcher.fetch_repositories(platform, token, url)
        
        if result['success']:
            return Response({
                'workspace_id': workspace.id,
                'workspace_name': workspace.name,
                'platform': workspace.platform,
                'repositories': result['repositories'],
                'total': len(result['repositories']),
                'message': result['message']
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'error': 'Failed to fetch repositories',
                'message': result['message']
            }, status=status.HTTP_400_BAD_REQUEST)