"""Pytest configuration and fixtures for authentication service tests."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


@pytest.fixture
def api_client():
    """Return an unauthenticated API client."""
    return APIClient()


@pytest.fixture
def user_data():
    """Return standard user data for testing."""
    return {
        'email': 'testuser@example.com',
        'password': 'SecurePass123!',
        'first_name': 'Test',
        'last_name': 'User',
        'position': 'Developer'
    }


@pytest.fixture
def create_user(db):
    """Factory fixture to create users."""
    def _create_user(email='testuser@example.com', password='SecurePass123!', **kwargs):
        user = User.objects.create_user(
            email=email,
            password=password,
            **kwargs
        )
        return user
    return _create_user


@pytest.fixture
def user(create_user):
    """Create and return a standard test user."""
    return create_user()


@pytest.fixture
def oauth_user(create_user):
    """Create and return an OAuth user."""
    return create_user(
        email='oauth@example.com',
        password=None,
        oauth_provider='github',
        oauth_id='12345'
    )


@pytest.fixture
def inactive_user(create_user):
    """Create and return an inactive user."""
    return create_user(
        email='inactive@example.com',
        is_active=False
    )


@pytest.fixture
def authenticated_client(api_client, user):
    """Return an authenticated API client."""
    refresh = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return api_client


@pytest.fixture
def tokens_for_user():
    """Factory to generate tokens for a user."""
    def _get_tokens(user):
        refresh = RefreshToken.for_user(user)
        return {
            'access': str(refresh.access_token),
            'refresh': str(refresh)
        }
    return _get_tokens
