"""
Pytest configuration and fixtures for Analyze Service tests.
"""
import pytest
from rest_framework.test import APIClient
from unittest.mock import Mock, patch, MagicMock
from analytics.models import Dataset, Analysis, AnalysisResult
from django.core.files.uploadedfile import SimpleUploadedFile
import uuid
from io import BytesIO


@pytest.fixture
def api_client():
    """Return an API client with X-User-ID header set."""
    client = APIClient()
    client.credentials(HTTP_X_USER_ID='1')
    return client


@pytest.fixture
def unauthenticated_client():
    """Return an API client without auth headers."""
    return APIClient()


@pytest.fixture
def sample_csv_content():
    """Return sample CSV content for testing."""
    return b"""title,state,created_at,merged_at,author,commits_count,additions,deletions
Test MR 1,merged,2024-01-01,2024-01-02,user1,5,100,50
Test MR 2,open,2024-01-03,,user2,3,50,25
Test MR 3,closed,2024-01-04,,user1,2,30,10
"""


@pytest.fixture
def csv_file(sample_csv_content):
    """Create a mock CSV file for upload."""
    return SimpleUploadedFile(
        name='test_data.csv',
        content=sample_csv_content,
        content_type='text/csv'
    )


@pytest.fixture
def create_dataset(db):
    """Factory fixture to create datasets."""
    def _create_dataset(
        workspace_id=1,
        repository_id=1,
        filename='test_data.csv',
        **kwargs
    ):
        defaults = {
            'file_path': 'datasets/test_data.csv',
            'rows_count': 100,
            'columns_count': 10,
            'platform': 'github'
        }
        defaults.update(kwargs)
        return Dataset.objects.create(
            workspace_id=workspace_id,
            repository_id=repository_id,
            filename=filename,
            **defaults
        )
    return _create_dataset


@pytest.fixture
def dataset(create_dataset):
    """Create and return a standard test dataset."""
    return create_dataset()


@pytest.fixture
def create_analysis(db, dataset):
    """Factory fixture to create analyses."""
    def _create_analysis(
        dataset=dataset,
        status='pending',
        metric_code='commits_over_time',
        chart_type='bar',
        **kwargs
    ):
        return Analysis.objects.create(
            dataset=dataset,
            status=status,
            metric_code=metric_code,
            chart_type=chart_type,
            **kwargs
        )
    return _create_analysis


@pytest.fixture
def analysis(create_analysis):
    """Create and return a standard test analysis."""
    return create_analysis()


@pytest.fixture
def completed_analysis(create_analysis):
    """Create and return a completed analysis."""
    return create_analysis(status='completed')


@pytest.fixture
def create_analysis_result(db, completed_analysis):
    """Factory fixture to create analysis results."""
    def _create_result(
        analysis=completed_analysis,
        **kwargs
    ):
        defaults = {
            'chart_image': 'base64_encoded_image_data',
            'chart_data': {'labels': ['Jan', 'Feb'], 'values': [10, 20]}
        }
        defaults.update(kwargs)
        return AnalysisResult.objects.create(
            analysis=analysis,
            **defaults
        )
    return _create_result


@pytest.fixture
def analysis_result(create_analysis_result):
    """Create and return a test analysis result."""
    return create_analysis_result()


@pytest.fixture
def mock_pandas_read_csv():
    """Mock pandas read_csv for testing."""
    with patch('pandas.read_csv') as mock:
        import pandas as pd
        mock.return_value = pd.DataFrame({
            'title': ['MR 1', 'MR 2'],
            'state': ['merged', 'open'],
            'created_at': ['2024-01-01', '2024-01-02'],
            'commits_count': [5, 3]
        })
        yield mock


@pytest.fixture
def mock_file_storage():
    """Mock Django file storage."""
    with patch('django.core.files.storage.default_storage') as mock:
        mock.save.return_value = 'datasets/test_data.csv'
        mock.path.return_value = '/tmp/datasets/test_data.csv'
        yield mock
