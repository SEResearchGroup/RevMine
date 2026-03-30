"""
Unit and Functional Tests for Analyze Service.
Tests cover dataset management, analysis creation, and chart generation.
"""
import pytest
from rest_framework import status
from unittest.mock import patch, Mock, MagicMock
from analytics.models import Dataset, Analysis, AnalysisResult
from django.core.files.uploadedfile import SimpleUploadedFile
import uuid


# =============================================================================
# Model Tests
# =============================================================================

@pytest.mark.django_db
class TestDatasetModel:
    """Unit tests for Dataset model."""

    def test_dataset_creation(self, create_dataset):
        """Test dataset creation with valid data."""
        dataset = create_dataset()
        assert dataset.id is not None
        assert dataset.filename == 'test_data.csv'

    def test_dataset_uuid_primary_key(self, create_dataset):
        """Test that dataset uses UUID as primary key."""
        dataset = create_dataset()
        assert isinstance(dataset.id, uuid.UUID)

    def test_dataset_str_representation(self, create_dataset):
        """Test dataset string representation."""
        dataset = create_dataset(filename='my_data.csv')
        assert 'my_data.csv' in str(dataset)


@pytest.mark.django_db
class TestAnalysisModel:
    """Unit tests for Analysis model."""

    def test_analysis_creation(self, create_analysis):
        """Test analysis creation with valid data."""
        analysis = create_analysis()
        assert analysis.id is not None
        assert analysis.status == 'pending'

    def test_analysis_requested_charts(self, create_analysis):
        """Test analysis stores requested charts."""
        charts = ['commits_over_time', 'lead_time_distribution']
        analysis = create_analysis(requested_charts=charts)
        assert analysis.requested_charts == charts

    def test_analysis_status_choices(self, create_analysis):
        """Test analysis status transitions."""
        analysis = create_analysis(status='pending')
        analysis.status = 'processing'
        analysis.save()
        analysis.refresh_from_db()
        assert analysis.status == 'processing'


@pytest.mark.django_db
class TestAnalysisResultModel:
    """Unit tests for AnalysisResult model."""

    def test_result_creation(self, create_analysis_result):
        """Test analysis result creation."""
        result = create_analysis_result()
        assert result.id is not None
        assert result.chart_type == 'commits_over_time'

    def test_result_chart_data(self, create_analysis_result):
        """Test result stores chart data."""
        result = create_analysis_result(
            chart_data={'labels': ['A', 'B'], 'values': [1, 2]}
        )
        assert result.chart_data['labels'] == ['A', 'B']


# =============================================================================
# Analysis API Tests
# =============================================================================

@pytest.mark.django_db
class TestAnalysisCreateEndpoint:
    """Functional tests for analysis creation endpoint."""

    def test_create_analysis_success(
        self, 
        api_client, 
        csv_file,
        mock_pandas_read_csv,
        mock_file_storage
    ):
        """Test successful analysis creation."""
        with patch('analytics.views.AnalysisCreateView._process_analysis'):
            response = api_client.post(
                '/api/analysis/create/',
                {
                    'csv_file': csv_file,
                    'requested_charts': ['commits_over_time'],
                    'platform': 'github'
                },
                format='multipart'
            )
            assert response.status_code == status.HTTP_201_CREATED
            assert 'id' in response.data

    def test_create_analysis_invalid_file_type(self, api_client):
        """Test analysis creation with non-CSV file fails."""
        invalid_file = SimpleUploadedFile(
            name='test.txt',
            content=b'not a csv',
            content_type='text/plain'
        )
        response = api_client.post(
            '/api/analysis/create/',
            {
                'csv_file': invalid_file,
                'requested_charts': ['commits_over_time']
            },
            format='multipart'
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_analysis_missing_charts(self, api_client, csv_file):
        """Test analysis creation without charts fails."""
        response = api_client.post(
            '/api/analysis/create/',
            {'csv_file': csv_file},
            format='multipart'
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_analysis_empty_charts(self, api_client, csv_file):
        """Test analysis creation with empty charts list fails."""
        response = api_client.post(
            '/api/analysis/create/',
            {
                'csv_file': csv_file,
                'requested_charts': []
            },
            format='multipart'
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestAnalysisListEndpoint:
    """Functional tests for analysis list endpoint."""

    def test_list_analyses(self, api_client, analysis):
        """Test listing all analyses."""
        response = api_client.get('/api/analysis/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1

    def test_list_analyses_filter_by_status(self, api_client, completed_analysis):
        """Test listing analyses filtered by status."""
        response = api_client.get('/api/analysis/?status=completed')
        assert response.status_code == status.HTTP_200_OK
        for item in response.data:
            assert item['status'] == 'completed'

    def test_list_analyses_filter_by_workspace(self, api_client, analysis):
        """Test listing analyses filtered by workspace."""
        response = api_client.get(f'/api/analysis/?workspace_id={analysis.dataset.workspace_id}')
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestAnalysisDetailEndpoint:
    """Functional tests for analysis detail endpoint."""

    def test_get_analysis_detail(self, api_client, completed_analysis, analysis_result):
        """Test getting analysis detail with results."""
        response = api_client.get(f'/api/analysis/{completed_analysis.id}/')
        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data
        assert response.data['status'] == 'completed'

    def test_get_analysis_not_found(self, api_client):
        """Test getting non-existent analysis returns 404."""
        fake_uuid = uuid.uuid4()
        response = api_client.get(f'/api/analysis/{fake_uuid}/')
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_analysis(self, api_client, analysis):
        """Test deleting an analysis."""
        analysis_id = analysis.id
        response = api_client.delete(f'/api/analysis/{analysis_id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Analysis.objects.filter(id=analysis_id).exists()


# =============================================================================
# Dataset API Tests
# =============================================================================

@pytest.mark.django_db
class TestDatasetEndpoints:
    """Functional tests for dataset endpoints."""

    def test_list_datasets(self, api_client, dataset):
        """Test listing all datasets."""
        response = api_client.get('/api/analysis/datasets/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1

    def test_get_dataset_detail(self, api_client, dataset):
        """Test getting dataset detail."""
        response = api_client.get(f'/api/analysis/datasets/{dataset.id}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['filename'] == dataset.filename

    def test_delete_dataset_cascades_analyses(self, api_client, dataset, analysis):
        """Test deleting dataset cascades to analyses."""
        analysis_id = analysis.id
        response = api_client.delete(f'/api/analysis/datasets/{dataset.id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Analysis.objects.filter(id=analysis_id).exists()


# =============================================================================
# Analysis Result Tests
# =============================================================================

@pytest.mark.django_db
class TestAnalysisResultEndpoints:
    """Functional tests for analysis result endpoints."""

    def test_get_result_detail(self, api_client, analysis_result):
        """Test getting specific analysis result."""
        response = api_client.get(f'/api/analysis/results/{analysis_result.id}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['chart_type'] == 'commits_over_time'
        assert 'chart_image' in response.data
