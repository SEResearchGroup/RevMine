"""
Pytest configuration and fixtures for Collection Service tests.
"""
import pytest
from rest_framework.test import APIClient
from unittest.mock import Mock, patch, MagicMock
from collectors.models import Collection, CleanedData
from datetime import datetime


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
def collection_data():
    """Return standard collection start data for testing."""
    return {
        'workspace_id': 1,
        'repository_id': 1,
        'repository_name': 'test-repo',
        'repository_full_name': 'owner/test-repo',
        'platform': 'github',
        'repository_url': 'https://github.com/owner/test-repo',
        'default_branch': 'main',
        'token': 'ghp_test_token_12345'
    }


@pytest.fixture
def metrics_config_data():
    """Return metrics configuration data for testing."""
    return {
        'selected_metrics': ['commits', 'pull_requests', 'contributors'],
        'branch_name': 'main',
        'start_date': '2024-01-01',
        'end_date': '2024-12-31',
        'status': ['open', 'closed', 'merged']
    }


@pytest.fixture
def create_collection(db):
    """Factory fixture to create collections."""
    def _create_collection(
        user_id=1, 
        workspace_id=1, 
        repository_id=1,
        status='pending',
        **kwargs
    ):
        defaults = {
            'repository_name': 'test-repo',
            'repository_full_name': 'owner/test-repo',
            'platform': 'github',
            'token_encrypted': 'encrypted_token',
            'selected_metrics': ['commits', 'pull_requests'],
            'filters': {},
        }
        defaults.update(kwargs)
        return Collection.objects.create(
            user=user_id,
            workspace_id=workspace_id,
            repository_id=repository_id,
            status=status,
            **defaults
        )
    return _create_collection


@pytest.fixture
def collection(create_collection):
    """Create and return a standard test collection."""
    return create_collection()


@pytest.fixture
def in_progress_collection(create_collection):
    """Create and return an in-progress collection."""
    return create_collection(
        status='in_progress',
        total_items=100,
        collected_items=50,
        last_collected_item_id='50'
    )


@pytest.fixture
def completed_collection(create_collection):
    """Create and return a completed collection."""
    return create_collection(
        status='completed',
        total_items=100,
        collected_items=100,
        raw_data_filename='test-repo_collection1_20240101_120000.json'
    )


@pytest.fixture
def create_cleaned_data(db, completed_collection):
    """Factory fixture to create cleaned data."""
    def _create_cleaned_data(collection=completed_collection, **kwargs):
        defaults = {
            'filters': {'status': ['merged']},
            'selected_features': ['pr_title', 'pr_author'],
            'structured_csv_filename': 'cleaned_data.csv',
            'statistics_csv_filename': 'statistics.csv',
            'status': 'completed',
            'stats': {'rows_count': 50},
        }
        defaults.update(kwargs)
        return CleanedData.objects.create(collection=collection, **defaults)
    return _create_cleaned_data


@pytest.fixture
def cleaned_data(create_cleaned_data):
    """Create and return test cleaned data."""
    return create_cleaned_data()


@pytest.fixture
def mock_minio_client():
    """Mock MinIO client for file operations."""
    with patch('collectors.minio_client.MinIOClient') as mock:
        instance = mock.return_value
        instance.save_json.return_value = True
        instance.save_csv.return_value = True
        instance.get_json.return_value = {'data': []}
        instance.get_csv.return_value = 'column1,column2\nvalue1,value2'
        instance.generate_filename.return_value = 'test_file.json'
        yield instance


@pytest.fixture
def mock_github_collector():
    """Mock GitHub collector for data collection."""
    with patch('collectors.github_collector.GitHubCollector') as mock:
        instance = mock.return_value
        instance.collect_data.return_value = {
            'pull_requests': [{'id': 1, 'title': 'Test PR'}],
            'commits': [{'sha': 'abc123', 'message': 'Test commit'}]
        }
        yield instance


@pytest.fixture
def mock_branch_fetcher():
    """Mock branch fetcher."""
    with patch('collectors.branch_fetcher.BranchFetcher') as mock:
        instance = mock.return_value
        instance.get_branches.return_value = [
            {'name': 'main', 'protected': True},
            {'name': 'develop', 'protected': False}
        ]
        yield instance
