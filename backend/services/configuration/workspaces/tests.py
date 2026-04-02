"""
Unit and Functional Tests for Configuration Service - Workspaces App.
Tests cover workspace CRUD operations, connection testing, and repository management.
"""
import pytest
from rest_framework import status
from unittest.mock import patch, Mock
from workspaces.models import Workspace, Repository
from workspaces.services import ConnectionService, GitAPIClient, RepositoryService


# =============================================================================
# Model Tests
# =============================================================================

@pytest.mark.django_db
class TestWorkspaceModel:
    """Unit tests for Workspace model."""

    def test_workspace_token_encryption(self, create_workspace):
        """Test that token is encrypted when stored."""
        workspace = create_workspace()
        assert workspace.token_encrypted != 'test_token_12345'
        assert workspace.get_token() == 'test_token_12345'

    def test_workspace_api_base_url_github(self, create_workspace):
        """Test GitHub API URL generation."""
        workspace = create_workspace(platform='github')
        assert workspace.get_api_base_url() == 'https://api.github.com'

    def test_workspace_api_base_url_gitlab(self, create_workspace):
        """Test GitLab API URL generation."""
        workspace = create_workspace(platform='gitlab')
        assert workspace.get_api_base_url() == 'https://gitlab.com/api/v4'

    def test_workspace_api_base_url_gitlab_self(self, create_workspace):
        """Test GitLab self-hosted API URL generation."""
        workspace = create_workspace(
            platform='gitlab_self',
            url='https://gitlab.company.com'
        )
        assert workspace.get_api_base_url() == 'https://gitlab.company.com/api/v4'

    def test_workspace_unique_name_per_user(self, create_workspace):
        """Test that workspace names are unique per user."""
        create_workspace(user_id=1, name='Unique Workspace')
        with pytest.raises(Exception):
            create_workspace(user_id=1, name='Unique Workspace')


# =============================================================================
# Connection Service Tests
# =============================================================================

@pytest.mark.django_db
class TestConnectionService:
    """Unit tests for ConnectionService."""

    @patch('workspaces.services.GitAPIClient.get')
    def test_test_connection_success(self, mock_get):
        """Test successful connection."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'login': 'testuser', 'id': 123}
        mock_get.return_value = mock_response

        result = ConnectionService.test_connection('github', 'valid_token')
        
        assert result['success'] is True
        assert 'user_data' in result

    @patch('workspaces.services.GitAPIClient.get')
    def test_test_connection_invalid_token(self, mock_get):
        """Test connection with invalid token."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        result = ConnectionService.test_connection('github', 'invalid_token')
        
        assert result['success'] is False


# =============================================================================
# Workspace API Tests
# =============================================================================

@pytest.mark.django_db
class TestWorkspaceListCreate:
    """Functional tests for workspace list and create endpoints."""

    def test_list_workspaces_authenticated(self, api_client, workspace):
        """Test listing workspaces for authenticated user."""
        response = api_client.get('/api/workspaces/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1

    def test_list_workspaces_unauthenticated(self, unauthenticated_client):
        """Test listing workspaces without authentication fails."""
        response = unauthenticated_client.get('/api/workspaces/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_workspace_success(self, api_client, workspace_data, mock_github_connection):
        """Test successful workspace creation."""
        response = api_client.post('/api/workspaces/', workspace_data)
        assert response.status_code == status.HTTP_201_CREATED
        assert 'workspace' in response.data
        assert response.data['workspace']['name'] == workspace_data['name']

    def test_create_workspace_invalid_platform(self, api_client, workspace_data):
        """Test workspace creation with invalid platform fails."""
        workspace_data['platform'] = 'invalid_platform'
        response = api_client.post('/api/workspaces/', workspace_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_workspace_gitlab_self_requires_url(self, api_client, gitlab_self_workspace_data):
        """Test GitLab self-hosted requires URL."""
        del gitlab_self_workspace_data['url']
        response = api_client.post('/api/workspaces/', gitlab_self_workspace_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_workspace_duplicate_name(self, api_client, workspace, workspace_data, mock_github_connection):
        """Test creating workspace with duplicate name fails with proper error."""
        workspace_data['name'] = workspace.name
        response = api_client.post('/api/workspaces/', workspace_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'already exists' in str(response.data).lower()


@pytest.mark.django_db
class TestWorkspaceDetail:
    """Functional tests for workspace detail, update, delete endpoints."""

    def test_get_workspace_detail(self, api_client, workspace):
        """Test getting workspace details."""
        response = api_client.get(f'/api/workspaces/{workspace.id}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == workspace.name

    def test_get_workspace_not_found(self, api_client):
        """Test getting non-existent workspace returns 404."""
        response = api_client.get('/api/workspaces/99999/')
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_workspace_partial(self, api_client, workspace, mock_github_connection):
        """Test partial update of workspace - should work without sending all fields."""
        response = api_client.patch(f'/api/workspaces/{workspace.id}/', {
            'name': 'Updated Name'
        })
        assert response.status_code == status.HTTP_200_OK
        workspace.refresh_from_db()
        assert workspace.name == 'Updated Name'

    def test_delete_workspace_success(self, api_client, workspace):
        """Test successful workspace deletion."""
        workspace_id = workspace.id
        response = api_client.delete(f'/api/workspaces/{workspace.id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Workspace.objects.filter(id=workspace_id).exists()

    def test_delete_workspace_cascades_repositories(self, api_client, workspace, repository):
        """Test that deleting workspace cascades to repositories."""
        repo_id = repository.id
        api_client.delete(f'/api/workspaces/{workspace.id}/')
        assert not Repository.objects.filter(id=repo_id).exists()


# =============================================================================
# Repository API Tests
# =============================================================================

@pytest.mark.django_db
class TestRepositoryEndpoints:
    """Functional tests for repository endpoints."""

    def test_list_repositories(self, api_client, workspace, repository):
        """Test listing repositories for a workspace."""
        response = api_client.get(f'/api/workspaces/{workspace.id}/repositories/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1

    def test_get_repository_detail(self, api_client, workspace, repository):
        """Test getting repository detail."""
        response = api_client.get(f'/api/workspaces/{workspace.id}/repositories/{repository.id}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == repository.name

    def test_delete_repository(self, api_client, workspace, repository):
        """Test deleting a repository."""
        repo_id = repository.id
        response = api_client.delete(f'/api/workspaces/{workspace.id}/repositories/{repository.id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Repository.objects.filter(id=repo_id).exists()

    @patch('workspaces.services.RepositoryService.fetch_repository_by_id')
    @patch('workspaces.services.RepositoryService.fetch_repositories')
    def test_import_repository_by_direct_external_id(
        self,
        mock_fetch_repositories,
        mock_fetch_repository_by_id,
        api_client,
        workspace,
    ):
        """Test importing a repository by ID even when it is not in the workspace list."""
        mock_fetch_repositories.return_value = {
            'success': True,
            'message': '0 repositories found',
            'repositories': [],
        }
        mock_fetch_repository_by_id.return_value = {
            'success': True,
            'message': 'Repository found',
            'repository': {
                'id': 987654321,
                'name': 'public-repo',
                'full_name': 'octocat/public-repo',
                'description': 'Public repository',
                'url': 'https://api.github.com/repos/octocat/public-repo',
                'html_url': 'https://github.com/octocat/public-repo',
                'owner': {'login': 'octocat', 'type': 'User'},
                'default_branch': 'main',
                'private': False,
                'fork': False,
                'archived': False,
                'created_at': '2024-01-01T00:00:00Z',
                'updated_at': '2024-02-01T00:00:00Z',
            },
        }

        response = api_client.post(
            f'/api/workspaces/{workspace.id}/repositories/import/',
            {'repository_ids': ['987654321']},
            format='json',
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['imported_count'] == 1
        assert Repository.objects.filter(
            workspace=workspace,
            external_id='987654321',
        ).exists()


@pytest.mark.django_db
class TestRepositoryService:
    """Unit tests for repository import fallbacks."""

    @patch('workspaces.services.RepositoryService.fetch_repository_by_id')
    @patch('workspaces.services.RepositoryService.fetch_repositories')
    def test_import_repositories_falls_back_to_direct_lookup(
        self,
        mock_fetch_repositories,
        mock_fetch_repository_by_id,
        workspace,
    ):
        """Test fallback import when repository is not present in workspace repository list."""
        mock_fetch_repositories.return_value = {
            'success': True,
            'message': '0 repositories found',
            'repositories': [],
        }
        mock_fetch_repository_by_id.return_value = {
            'success': True,
            'message': 'Repository found',
            'repository': {
                'id': 456789,
                'name': 'fallback-repo',
                'full_name': 'octocat/fallback-repo',
                'description': 'Fallback repository',
                'url': 'https://api.github.com/repos/octocat/fallback-repo',
                'html_url': 'https://github.com/octocat/fallback-repo',
                'owner': {'login': 'octocat', 'type': 'User'},
                'default_branch': 'main',
                'private': False,
                'fork': False,
                'archived': False,
                'created_at': '2024-01-01T00:00:00Z',
                'updated_at': '2024-02-01T00:00:00Z',
            },
        }

        imported_repositories, errors = RepositoryService.import_repositories(
            workspace,
            ['456789'],
        )

        assert len(imported_repositories) == 1
        assert errors == []
        assert imported_repositories[0].external_id == '456789'


# =============================================================================
# Connection Test Endpoint Tests
# =============================================================================

@pytest.mark.django_db
class TestConnectionEndpoint:
    """Functional tests for connection test endpoint."""

    def test_test_new_connection(self, api_client, mock_github_connection):
        """Test testing a new connection without workspace."""
        response = api_client.post('/api/workspaces/test/', {
            'platform': 'github',
            'token': 'test_token'
        })
        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True

    def test_test_existing_workspace_connection(self, api_client, workspace, mock_github_connection):
        """Test testing connection for existing workspace."""
        response = api_client.post(f'/api/workspaces/{workspace.id}/test/')
        assert response.status_code == status.HTTP_200_OK
