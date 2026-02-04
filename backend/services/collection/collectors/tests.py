"""
Unit and Functional Tests for Collection Service.
Tests cover collection CRUD, metrics, data cleaning, and MinIO integration.
"""
import pytest
from rest_framework import status
from unittest.mock import patch, Mock, MagicMock
from collectors.models import Collection, CleanedData
from collectors.services import (
    MetricsService,
    BranchService,
    CollectionService,
    CollectionServiceError,
)
from collectors.minio_client import MinIOClient


# =============================================================================
# Model Tests
# =============================================================================

@pytest.mark.django_db
class TestCollectionModel:
    """Unit tests for Collection model."""

    def test_collection_progress_percentage(self, create_collection):
        """Test progress percentage calculation."""
        collection = create_collection(total_items=100, collected_items=50)
        assert collection.progress_percentage == 50

    def test_collection_progress_percentage_zero_items(self, create_collection):
        """Test progress percentage with zero total items."""
        collection = create_collection(total_items=0, collected_items=0)
        assert collection.progress_percentage == 0

    def test_collection_can_resume_paused(self, create_collection):
        """Test can_resume for paused collection."""
        collection = create_collection(
            status='paused',
            last_collected_item_id='50'
        )
        assert collection.can_resume is True

    def test_collection_can_resume_no_progress(self, create_collection):
        """Test can_resume when no progress made."""
        collection = create_collection(status='paused')
        assert collection.can_resume is False

    def test_collection_is_active_pending(self, create_collection):
        """Test is_active for pending collection."""
        collection = create_collection(status='pending')
        assert collection.is_active is True

    def test_collection_is_active_completed(self, create_collection):
        """Test is_active for completed collection."""
        collection = create_collection(status='completed')
        assert collection.is_active is False

    def test_get_active_for_repository(self, create_collection):
        """Test getting active collection for repository."""
        collection = create_collection(status='in_progress')
        result = Collection.get_active_for_repository(
            user_id=1,
            repository_id=1
        )
        assert result == collection


# =============================================================================
# MinIO Client Tests (Mocked)
# =============================================================================

@pytest.mark.django_db
class TestMinIOClient:
    """Unit tests for MinIO client."""

    def test_generate_filename(self, mock_minio_client):
        """Test filename generation."""
        filename = mock_minio_client.generate_filename('test-repo', 1, 'json')
        assert filename == 'test_file.json'

    def test_save_json_success(self, mock_minio_client):
        """Test successful JSON save."""
        result = mock_minio_client.save_json({'data': []}, 'test.json')
        assert result is True

    def test_get_json_success(self, mock_minio_client):
        """Test successful JSON retrieval."""
        result = mock_minio_client.get_json('test.json')
        assert result == {'data': []}


# =============================================================================
# Metrics Service Tests
# =============================================================================

@pytest.mark.django_db
class TestMetricsService:
    """Unit tests for MetricsService."""

    def test_get_available_metrics_github(self):
        """Test getting available metrics for GitHub."""
        metrics = MetricsService.get_available_metrics('github')
        # Returns a dict with categories as keys
        assert isinstance(metrics, dict)
        assert len(metrics) > 0
        assert 'Pull Request Metadata' in metrics

    def test_get_metrics_with_collection_status_no_active(self):
        """Test metrics with no active collection."""
        result = MetricsService.get_metrics_with_collection_status(
            user_id=1,
            repository_id=999,
            platform='github'
        )
        assert result['has_active_collection'] is False

    def test_get_metrics_with_active_collection(self, in_progress_collection):
        """Test metrics with active collection."""
        result = MetricsService.get_metrics_with_collection_status(
            user_id=1,
            repository_id=1,
            platform='github'
        )
        assert result['has_active_collection'] is True
        assert result['active_collection'] == in_progress_collection


# =============================================================================
# Collection API Tests
# =============================================================================

@pytest.mark.django_db
class TestMetricsEndpoint:
    """Functional tests for metrics endpoint."""

    def test_get_available_metrics(self, api_client):
        """Test getting available metrics."""
        response = api_client.get('/api/collections/metrics/?repository_id=1&platform=github')
        assert response.status_code == status.HTTP_200_OK
        assert 'available_metrics' in response.data

    def test_get_metrics_without_repository_id(self, api_client):
        """Test getting metrics without repository_id fails."""
        response = api_client.get('/api/collections/metrics/?platform=github')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_get_metrics_unauthenticated(self, unauthenticated_client):
        """Test getting metrics without auth fails."""
        response = unauthenticated_client.get('/api/collections/metrics/?repository_id=1')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestCollectionPlanEndpoints:
    """Functional tests for collection plan endpoints."""

    def test_list_collection_plans(self, api_client, collection):
        """Test listing collection plans."""
        response = api_client.get('/api/collections/plans/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1

    def test_get_collection_status(self, api_client, collection):
        """Test getting collection status."""
        response = api_client.get(f'/api/collections/plans/{collection.id}/status/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'pending'

    def test_configure_collection_metrics(self, api_client, collection, metrics_config_data):
        """Test configuring collection metrics."""
        response = api_client.post(
            f'/api/collections/plans/{collection.id}/configure/',
            metrics_config_data
        )
        assert response.status_code == status.HTTP_200_OK
        collection.refresh_from_db()
        assert collection.selected_metrics == metrics_config_data['selected_metrics']

    def test_configure_metrics_invalid_dates(self, api_client, collection):
        """Test configuring with invalid date range fails."""
        response = api_client.post(
            f'/api/collections/plans/{collection.id}/configure/',
            {
                'selected_metrics': ['commits'],
                'start_date': '2024-12-31',
                'end_date': '2024-01-01'  # End before start
            }
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_delete_collection(self, api_client, completed_collection):
        """Test deleting a completed collection."""
        collection_id = completed_collection.id
        response = api_client.delete(f'/api/collections/collections/{collection_id}/delete/')
        # API returns 200 with success message
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_204_NO_CONTENT]
        assert not Collection.objects.filter(id=collection_id).exists()


@pytest.mark.django_db
class TestCollectionHistory:
    """Functional tests for collection history endpoint."""

    def test_get_collection_history(self, api_client, completed_collection):
        """Test getting collection history for repository."""
        response = api_client.get(f'/api/collections/history/{completed_collection.repository_id}/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1


# =============================================================================
# Cleaned Data API Tests
# =============================================================================

@pytest.mark.django_db
class TestCleanedDataEndpoints:
    """Functional tests for cleaned data endpoints."""

    def test_list_cleaned_data_for_collection(self, api_client, completed_collection, cleaned_data):
        """Test listing cleaned data for a collection."""
        response = api_client.get(
            f'/api/collections/collections/{completed_collection.id}/cleaned-data/'
        )
        assert response.status_code == status.HTTP_200_OK

    def test_create_cleaned_data(self, api_client, completed_collection, mock_minio_client):
        """Test creating cleaned data."""
        with patch('collectors.services.CleanedDataService.create_cleaned_data') as mock_create:
            mock_create.return_value = CleanedData(
                id=1,
                collection=completed_collection,
                filters={'status': ['merged']},
                selected_features=['pr_title'],
                structured_csv_filename='cleaned.csv'
            )
            response = api_client.post('/api/collections/cleaned-data/', {
                'collection_id': completed_collection.id,
                'filters': {'status': ['merged']}
            }, format='json')
            # Note: actual status depends on implementation
            assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]

    def test_get_cleaned_data_detail(self, api_client, cleaned_data):
        """Test getting cleaned data detail."""
        response = api_client.get(f'/api/collections/cleaned-data/{cleaned_data.id}/')
        assert response.status_code == status.HTTP_200_OK

    def test_delete_cleaned_data(self, api_client, cleaned_data):
        """Test deleting cleaned data."""
        cleaned_data_id = cleaned_data.id
        response = api_client.delete(f'/api/collections/cleaned-data/{cleaned_data_id}/')
        # API returns 200 with success message
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_204_NO_CONTENT]
        assert not CleanedData.objects.filter(id=cleaned_data_id).exists()


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================

@pytest.mark.django_db
class TestCollectionEdgeCases:
    """Tests for edge cases and error handling."""

    def test_access_other_user_collection(self, api_client, create_collection):
        """Test user cannot access another user's collection."""
        other_collection = create_collection(user_id=999)
        response = api_client.get(f'/api/collections/plans/{other_collection.id}/status/')
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_execute_already_completed_collection(self, api_client, completed_collection):
        """Test executing already completed collection fails."""
        response = api_client.post(f'/api/collections/plans/{completed_collection.id}/execute/')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_resume_non_resumable_collection(self, api_client, collection):
        """Test resuming collection without progress fails."""
        response = api_client.post(f'/api/collections/plans/{collection.id}/resume/')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
