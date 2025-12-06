from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample, OpenApiResponse
from drf_spectacular.types import OpenApiTypes
from .serializers import WorkspaceSerializer, WorkspaceListSerializer, TestConnectionSerializer, RepositorySerializer
from django.utils import timezone
from django.db.models import Q
from datetime import datetime
import requests
from .models import Workspace, Repository


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




class WorkspaceTokenView(APIView):
    """
    Internal endpoint to get workspace token (for inter-service communication)
    """
    @extend_schema(
        summary="Get workspace token (internal)",
        description="Retrieve decrypted workspace token for inter-service use",
        tags=["Workspaces - Internal"],
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
            401: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        }
    )
    def get(self, request, workspace_id):
        """Retrieve workspace token"""
        if not request.user_id:
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        workspace = get_object_or_404(Workspace, id=workspace_id, user=request.user_id)
        
        return Response({
            'token': workspace.get_token(),
            'platform': workspace.platform,
            'url': workspace.url
        })


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
        

class RepositoryImportView(APIView):
    """
    POST: Import selected repositories into the database
    Body: { "repository_ids": ["123", "456", "789"] }
    """
    
    @extend_schema(
        summary="Import selected repositories",
        description="Imports the selected Git repositories into the database using their external IDs.",
        tags=["Repositories"],
        parameters=[
            OpenApiParameter(
                name='workspace_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description='ID of the workspace to import repositories into'
            ),
        ],
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'repository_ids': {
                        'type': 'array',
                        'items': {'type': 'string'},
                        'description': 'List of external IDs (GitHub/GitLab) of the repositories to import'
                    }
                },
                'required': ['repository_ids'],
                'example': {'repository_ids': ['123456789', '987654321']}
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
                name='Valid request',
                value={'repository_ids': ['123456789', '987654321']},
                request_only=True,
            ),
            OpenApiExample(
                name='Success response',
                value={
                    'success': True,
                    'imported_count': 2,
                    'repositories': [
                        {
                            'id': 5,
                            'workspace': 1,
                            'external_id': '123456789',
                            'name': 'my-project',
                            'full_name': 'user/my-project',
                            'is_active': True,
                            'imported_at': '2025-11-25T20:00:00Z'
                        }
                    ],
                    'errors': []
                },
                response_only=True,
            ),
            OpenApiExample(
                name='Partial error',
                value={
                    'success': True,
                    'imported_count': 1,
                    'repositories': [
                        {
                            "id": 1,
                            "workspace": 2,
                            "workspace_name": "My workspace",
                            "platform": "github",
                            "external_id": "1122",
                            "name": "dashboard",
                            "full_name": "xxyy/dashboard",
                            "description": "Dashboard project",
                            "url": "https://api.github.com/repos/xxyy/dashboard",
                            "web_url": "https://github.com/xxyy/dashboard",
                            "owner": "xxyy",
                            "owner_type": "User",
                            "default_branch": "main",
                            "language": "JavaScript",
                            "stars_count": 0,
                            "forks_count": 0,
                            "open_issues_count": 0,
                            "is_private": "true",
                            "is_fork": "false",
                            "is_archived": "false",
                            "is_active": "true",
                            "created_at_platform": "2022-09-11T20:21:51Z",
                            "last_activity_at": "2025-11-23T17:37:08Z",
                            "last_analyzed_at": "null",
                            "imported_at": "2025-11-25T19:23:42.871826Z",
                            "updated_at": "2025-11-25T19:23:42.871834Z"
                        }
                    ],
                    'errors': [
                        {'repository': 'unknown-repo', 'error': 'Repository not found or inaccessible'}
                    ]
                },
                response_only=True,
            ),
        ]
    )
    def post(self, request, workspace_id):
        workspace = get_object_or_404(Workspace, id=workspace_id)
        repository_ids = request.data.get('repository_ids', [])
        
        if not repository_ids:
            return Response(
                {'error': 'Aucun repository sélectionné'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Récupérer tous les repos disponibles depuis la plateforme
            all_repos = self._fetch_all_repositories(workspace)
            
            # Filtrer les repos sélectionnés
            selected_repos = [
                repo for repo in all_repos 
                if str(repo.get('id')) in [str(rid) for rid in repository_ids]
            ]
            
            if not selected_repos:
                return Response(
                    {'error': 'Aucun repository trouvé avec les IDs fournis'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Importer les repositories
            imported_repos = []
            errors = []
            
            for repo_data in selected_repos:
                try:
                    repo = self._import_repository(workspace, repo_data)
                    imported_repos.append(repo)
                except Exception as e:
                    errors.append({
                        'repository': repo_data.get('name'),
                        'error': str(e)
                    })
            
            # Mettre à jour last_sync du workspace
            workspace.last_sync = timezone.now()
            workspace.save()
            
            return Response({
                'success': True,
                'imported_count': len(imported_repos),
                'repositories': RepositorySerializer(imported_repos, many=True).data,
                'errors': errors
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': f'Erreur lors de l\'import: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _fetch_all_repositories(self, workspace):
        """Fetch all repositories from the API"""
        headers = self._get_headers(workspace)
        base_url = workspace.get_api_base_url()
        
        if workspace.platform == 'github':
            response = requests.get(
                f'{base_url}/user/repos',
                headers=headers,
                params={'per_page': 100, 'sort': 'updated'}
            )
        else:  # GitLab
            response = requests.get(
                f'{base_url}/projects',
                headers=headers,
                params={'per_page': 100, 'membership': True, 'order_by': 'last_activity_at'}
            )
        
        response.raise_for_status()
        return response.json()
    
    def _import_repository(self, workspace, repo_data):
        """Normalize and import a repository"""
        normalized_data = self._normalize_repository_data(workspace, repo_data)
        
        repository, created = Repository.objects.update_or_create(
            workspace=workspace,
            external_id=normalized_data['external_id'],
            defaults=normalized_data
        )
        
        return repository
    
    def _normalize_repository_data(self, workspace, repo_data):
        """Normalize data between GitHub and GitLab"""
        if workspace.platform == 'github':
            return self._normalize_github_data(repo_data)
        else:
            return self._normalize_gitlab_data(repo_data)
    
    def _normalize_github_data(self, repo):
        """Normalize GitHub data"""
        return {
            'external_id': str(repo['id']),
            'name': repo['name'],
            'full_name': repo['full_name'],
            'description': repo.get('description'),
            'url': repo['url'],
            'web_url': repo['html_url'],
            'owner': repo['owner']['login'],
            'owner_type': repo['owner']['type'],
            'default_branch': repo.get('default_branch', 'main'),
            'language': repo.get('language'),
            'stars_count': repo.get('stargazers_count', 0),
            'forks_count': repo.get('forks_count', 0),
            'open_issues_count': repo.get('open_issues_count', 0),
            'is_private': repo.get('private', False),
            'is_fork': repo.get('fork', False),
            'is_archived': repo.get('archived', False),
            'created_at_platform': self._parse_datetime(repo['created_at']),
            'last_activity_at': self._parse_datetime(repo['updated_at']),
            'raw_data': repo,
        }
    
    def _normalize_gitlab_data(self, repo):
        """Normalize GitLab data"""
        return {
            'external_id': str(repo['id']),
            'name': repo['name'],
            'full_name': repo['path_with_namespace'],
            'description': repo.get('description'),
            'url': repo['_links']['self'],
            'web_url': repo['web_url'],
            'owner': repo['namespace']['full_path'],
            'owner_type': repo['namespace']['kind'],
            'default_branch': repo.get('default_branch', 'main'),
            'language': None,  # GitLab ne fournit pas directement le langage principal
            'stars_count': repo.get('star_count', 0),
            'forks_count': repo.get('forks_count', 0),
            'open_issues_count': repo.get('open_issues_count', 0),
            'is_private': repo.get('visibility') == 'private',
            'is_fork': 'forked_from_project' in repo,
            'is_archived': repo.get('archived', False),
            'created_at_platform': self._parse_datetime(repo['created_at']),
            'last_activity_at': self._parse_datetime(repo.get('last_activity_at')),
            'raw_data': repo,
        }
    
    def _parse_datetime(self, dt_string):
        """Parse ISO 8601 dates"""
        if not dt_string:
            return None
        try:
            return datetime.fromisoformat(dt_string.replace('Z', '+00:00'))
        except:
            return None
    
    def _get_headers(self, workspace):
        """Construct authentication headers"""
        token = workspace.get_token()
        if workspace.platform == 'github':
            return {
                'Authorization': f'token {token}',
                'Accept': 'application/vnd.github.v3+json'
            }
        else:
            return {'PRIVATE-TOKEN': token}


class RepositoryListView(APIView):
    """
    GET: List all imported repositories
    Query params: ?workspace_id=X, ?is_active=true, ?search=name
    """
    @extend_schema(
        summary="List imported repositories of a workspace",
        description="Returns the list of repositories already imported into a workspace, with optional filters.",
        tags=["Repositories"],
        parameters=[
            OpenApiParameter(
                name='workspace_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description='Workspace ID',
                required=True,
            ),
            OpenApiParameter(
                name='is_active',
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description='Filter by active state (true/false)',
                required=False,
            ),
            OpenApiParameter(
                name='search',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Text search in name or full_name',
                required=False,
            ),
        ],
        responses={200: RepositorySerializer(many=True)},
        examples=[
            OpenApiExample(
                name='Example response',
                value=[
                    {
                        'id': 3,
                        'workspace': 1,
                        'workspace_name': 'My GitHub Workspace',
                        'platform': 'github',
                        'external_id': '112233445',
                        'name': 'api-service',
                        'full_name': 'company/api-service',
                        'description': 'Service API principal',
                        'web_url': 'https://github.com/company/api-service',
                        'default_branch': 'main',
                        'language': 'Python',
                        'is_private': True,
                        'is_active': True,
                        'imported_at': '2025-11-20T14:30:22Z',
                        'last_activity_at': '2025-11-24T09:15:00Z'
                    }
                ],
                response_only=True,
            )
        ]
    )
    
    def get(self, request, workspace_id):
        """
        List all imported repositories for a workspace, with optional filtering.
        """
        queryset = Repository.objects.filter(workspace_id=workspace_id)

        is_active = request.query_params.get("is_active")
        if is_active is not None:
            if is_active.lower() in ["true", "1"]:
                queryset = queryset.filter(is_active=True)
            elif is_active.lower() in ["false", "0"]:
                queryset = queryset.filter(is_active=False)

        search = request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(full_name__icontains=search)
            )

        serializer = RepositorySerializer(queryset, many=True)
        return Response(serializer.data)


class RepositoryDetailView(APIView):
    """
    GET: Retrieve repository details.
    PATCH: Update selected fields (e.g., is_active, description).
    DELETE: Delete the repository.
    """

    @extend_schema(
        summary="DDetail of an imported repository",
        description="Retrieves all information of a previously imported repository.",
        tags=["Repositories"],
        parameters=[
            OpenApiParameter(
                name='repository_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description='Internal ID of the repository in the application',
                required=True,
            ),
        ],
        responses={200: RepositorySerializer},
        examples=[
            OpenApiExample(
                name='Detailed repository',
                value={
                    'id': 7,
                    'workspace': 2,
                    'workspace_name': 'Entreprise GitLab',
                    'platform': 'gitlab_self',
                    'external_id': '4455',
                    'name': 'frontend-app',
                    'full_name': 'frontend/frontend-app',
                    'description': 'Application React principale',
                    'web_url': 'https://gitlab.company.com/frontend/frontend-app',
                    'default_branch': 'master',
                    'language': None,
                    'is_private': True,
                    'is_active': True,
                    'is_fork': False,
                    'is_archived': False,
                    'created_at_platform': '2023-06-15T08:22:11Z',
                    'last_activity_at': '2025-11-25T12:04:33Z',
                    'imported_at': '2025-11-01T10:15:44Z'
                },
                response_only=True,
            )
        ]
    )
    def get(self, request, workspace_id, repository_id):
        repository = get_object_or_404(Repository, id=repository_id, workspace_id=workspace_id)
        serializer = RepositorySerializer(repository)
        return Response(serializer.data)
    
    @extend_schema(
        summary="Mettre à jour un repository importé",
        description="Modification partielle autorisée uniquement sur les champs `is_active` et `description`.",
        tags=["Repositories"],
        parameters=[
            OpenApiParameter(
                name='repository_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                required=True,
            ),
        ],
        request=OpenApiTypes.OBJECT,
        responses={200: RepositorySerializer},
        examples=[
            OpenApiExample(
                name='Exemple PATCH',
                value={'is_active': False, 'description': 'Projet archivé temporairement'},
                request_only=True,
            )
        ]
    )
    def patch(self, request, repository_id):
        repository = get_object_or_404(Repository, id=repository_id)
        
        allowed_fields = ['is_active', 'description']
        update_data = {
            k: v for k, v in request.data.items() 
            if k in allowed_fields
        }
        
        for key, value in update_data.items():
            setattr(repository, key, value)
        
        repository.save()
        serializer = RepositorySerializer(repository)
        return Response(serializer.data)
    
    
    @extend_schema(
        summary="Delete an imported repository",
        description="Permanently deletes a repository from the database (does not affect the remote repository).",
        tags=["Repositories"],
        parameters=[
            OpenApiParameter(
                name='repository_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                required=True,
            ),
        ],
        responses={204: None}
    )
    def delete(self, request, repository_id):
        repository = get_object_or_404(Repository, id=repository_id)
        repository.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
