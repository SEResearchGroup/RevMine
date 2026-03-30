"""
Pytest configuration and fixtures for Configuration Service tests.
"""
import pytest
from rest_framework.test import APIClient
from unittest.mock import Mock, patch
from workspaces.models import Workspace, Repository


@pytest.fixture
def api_client():
    """Return an API client with user ID header."""
    client = APIClient()
    client.credentials(HTTP_X_USER_ID='1')
    return client


@pytest.fixture
def unauthenticated_client():
    """Return an unauthenticated API client."""
    return APIClient()


@pytest.fixture
def workspace_data():
    """Return standard workspace data for testing."""
    return {
        'name': 'Test Workspace',
        'description': 'Test description',
        'platform': 'github',
        'token': 'ghp_test_token_12345'
    }


@pytest.fixture
def gitlab_workspace_data():
    """Return GitLab workspace data for testing."""
    return {
        'name': 'GitLab Workspace',
        'description': 'GitLab test',
        'platform': 'gitlab',
        'token': 'glpat-test_token_12345'
    }


@pytest.fixture
def gitlab_self_workspace_data():
    """Return GitLab self-hosted workspace data for testing."""
    return {
        'name': 'GitLab Self Workspace',
        'description': 'GitLab self-hosted test',
        'platform': 'gitlab_self',
        'url': 'https://gitlab.company.com',
        'token': 'glpat-self_token_12345'
    }


@pytest.fixture
def create_workspace(db):
    """Factory fixture to create workspaces."""
    def _create_workspace(user_id=1, name='Test Workspace', platform='github', **kwargs):
        workspace = Workspace(
            user=user_id,
            name=name,
            platform=platform,
            **kwargs
        )
        workspace.set_token('test_token_12345')
        workspace.save()
        return workspace
    return _create_workspace


@pytest.fixture
def workspace(create_workspace):
    """Create and return a standard test workspace."""
    return create_workspace()


@pytest.fixture
def create_repository(db, workspace):
    """Factory fixture to create repositories."""
    def _create_repository(workspace=workspace, **kwargs):
        defaults = {
            'external_id': '12345',
            'name': 'test-repo',
            'full_name': 'owner/test-repo',
            'description': 'A test repository',
            'url': 'https://api.github.com/repos/owner/test-repo',
            'web_url': 'https://github.com/owner/test-repo',
            'owner': 'owner',
            'owner_type': 'User',
            'default_branch': 'main',
            'created_at_platform': '2024-01-01T00:00:00Z',
        }
        defaults.update(kwargs)
        return Repository.objects.create(workspace=workspace, **defaults)
    return _create_repository


@pytest.fixture
def repository(create_repository):
    """Create and return a test repository."""
    return create_repository()


@pytest.fixture
def mock_github_connection():
    """Mock successful GitHub connection test."""
    with patch('workspaces.services.ConnectionService.test_connection') as mock:
        mock.return_value = {
            'success': True,
            'message': 'Connection successful',
            'user_data': {'login': 'testuser', 'id': 123}
        }
        yield mock


@pytest.fixture
def mock_github_repos():
    """Mock GitHub repository fetch."""
    with patch('workspaces.services.RepositoryService.fetch_remote_repositories') as mock:
        mock.return_value = [
            {
                'id': '12345',
                'name': 'test-repo',
                'full_name': 'owner/test-repo',
                'description': 'Test repo',
                'html_url': 'https://github.com/owner/test-repo',
                'clone_url': 'https://github.com/owner/test-repo.git',
                'owner': {'login': 'owner', 'type': 'User'},
                'default_branch': 'main',
                'private': False,
                'fork': False,
                'archived': False,
                'created_at': '2024-01-01T00:00:00Z',
                'pushed_at': '2024-01-15T00:00:00Z',
            }
        ]
        yield mock
