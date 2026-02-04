"""
Unit and Functional Tests for API Gateway Users App.
Tests cover authentication, user management, and authorization flows.
"""
import pytest
from django.urls import reverse
from rest_framework import status
from django.contrib.auth import get_user_model

User = get_user_model()


# =============================================================================
# User Model Tests
# =============================================================================

@pytest.mark.django_db
class TestUserModel:
    """Unit tests for User model."""

    def test_create_user_with_email(self, create_user):
        """Test creating a user with email succeeds."""
        user = create_user(email='new@example.com')
        assert user.email == 'new@example.com'
        assert user.is_active is True
        assert user.is_staff is False

    def test_create_user_without_email_raises(self):
        """Test creating user without email raises ValueError."""
        with pytest.raises(ValueError, match='Email is required'):
            User.objects.create_user(email='', password='test123')

    def test_create_superuser(self, db):
        """Test creating a superuser."""
        admin = User.objects.create_superuser(
            email='admin@example.com',
            password='AdminPass123!'
        )
        assert admin.is_staff is True
        assert admin.is_superuser is True

    def test_user_email_normalized(self, create_user):
        """Test email is normalized on user creation."""
        user = create_user(email='Test@EXAMPLE.COM')
        assert user.email == 'Test@example.com'


# =============================================================================
# Registration Tests
# =============================================================================

@pytest.mark.django_db
class TestRegistration:
    """Functional tests for user registration endpoint."""

    def test_register_success(self, api_client, user_data):
        """Test successful user registration."""
        response = api_client.post('/api/auth/register', user_data)
        assert response.status_code == status.HTTP_201_CREATED
        assert User.objects.filter(email=user_data['email']).exists()

    def test_register_duplicate_email(self, api_client, user, user_data):
        """Test registration with existing email fails."""
        user_data['email'] = user.email
        response = api_client.post('/api/auth/register', user_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_invalid_email(self, api_client, user_data):
        """Test registration with invalid email fails."""
        user_data['email'] = 'invalid-email'
        response = api_client.post('/api/auth/register', user_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_missing_password(self, api_client, user_data):
        """Test registration without password fails."""
        del user_data['password']
        response = api_client.post('/api/auth/register', user_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# Login Tests
# =============================================================================

@pytest.mark.django_db
class TestLogin:
    """Functional tests for user login endpoint."""

    def test_login_success(self, api_client, user, user_data):
        """Test successful login returns tokens."""
        response = api_client.post('/api/auth/login', {
            'email': user.email,
            'password': user_data['password']
        })
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data
        assert 'refresh' in response.data
        assert 'user' in response.data

    def test_login_wrong_password(self, api_client, user):
        """Test login with wrong password fails."""
        response = api_client.post('/api/auth/login', {
            'email': user.email,
            'password': 'WrongPassword!'
        })
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data['error'] == 'Invalid credentials'

    def test_login_nonexistent_user(self, api_client):
        """Test login with non-existent email fails."""
        response = api_client.post('/api/auth/login', {
            'email': 'nonexistent@example.com',
            'password': 'SomePass123!'
        })
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_inactive_user(self, api_client, inactive_user):
        """Test login with inactive user fails."""
        response = api_client.post('/api/auth/login', {
            'email': inactive_user.email,
            'password': 'SecurePass123!'
        })
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data['error'] == 'Account is disabled'

    def test_login_oauth_user_with_password_fails(self, api_client, oauth_user):
        """Test OAuth user cannot login with password."""
        response = api_client.post('/api/auth/login', {
            'email': oauth_user.email,
            'password': 'any_password'
        })
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# =============================================================================
# Protected Endpoint Tests (Me/Profile)
# =============================================================================

@pytest.mark.django_db
class TestMeEndpoint:
    """Functional tests for /me endpoint."""

    def test_get_me_authenticated(self, authenticated_client, user):
        """Test getting current user info when authenticated."""
        response = authenticated_client.get('/api/auth/me')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['email'] == user.email

    def test_get_me_unauthenticated(self, api_client):
        """Test getting current user info without auth fails."""
        response = api_client.get('/api/auth/me')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestUpdateUser:
    """Functional tests for user update endpoint."""

    def test_update_user_partial(self, authenticated_client, user):
        """Test partial update of user data."""
        response = authenticated_client.patch('/api/auth/me/update/', {
            'first_name': 'Updated'
        })
        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.first_name == 'Updated'

    def test_update_user_full(self, authenticated_client, user):
        """Test full update of user data."""
        response = authenticated_client.put('/api/auth/me/update/', {
            'email': user.email,
            'first_name': 'New',
            'last_name': 'Name',
            'position': 'Manager'
        })
        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.first_name == 'New'
        assert user.position == 'Manager'

    def test_update_email_duplicate(self, authenticated_client, user, create_user):
        """Test updating email to existing email fails."""
        other_user = create_user(email='other@example.com')
        response = authenticated_client.patch('/api/auth/me/update/', {
            'email': other_user.email
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_update_unauthenticated(self, api_client):
        """Test update without authentication fails."""
        response = api_client.patch('/api/auth/me/update/', {
            'first_name': 'Test'
        })
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# =============================================================================
# Change Password Tests
# =============================================================================

@pytest.mark.django_db
class TestChangePassword:
    """Functional tests for password change endpoint."""

    def test_change_password_success(self, authenticated_client, user, user_data):
        """Test successful password change."""
        response = authenticated_client.post('/api/auth/me/change-password/', {
            'old_password': user_data['password'],
            'new_password': 'NewSecurePass456!',
            'new_password_confirm': 'NewSecurePass456!'
        })
        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.check_password('NewSecurePass456!')

    def test_change_password_wrong_old(self, authenticated_client):
        """Test password change with wrong old password fails."""
        response = authenticated_client.post('/api/auth/me/change-password/', {
            'old_password': 'WrongOldPass!',
            'new_password': 'NewSecurePass456!',
            'new_password_confirm': 'NewSecurePass456!'
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_change_password_mismatch(self, authenticated_client, user_data):
        """Test password change with mismatched confirmation fails."""
        response = authenticated_client.post('/api/auth/me/change-password/', {
            'old_password': user_data['password'],
            'new_password': 'NewSecurePass456!',
            'new_password_confirm': 'DifferentPass789!'
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# Delete User Tests
# =============================================================================

@pytest.mark.django_db
class TestDeleteUser:
    """Functional tests for user deletion endpoint."""

    def test_delete_user_success(self, authenticated_client, user):
        """Test successful user deletion."""
        user_id = user.id
        response = authenticated_client.delete('/api/auth/me/delete/')
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not User.objects.filter(id=user_id).exists()

    def test_delete_user_unauthenticated(self, api_client):
        """Test deletion without authentication fails."""
        response = api_client.delete('/api/auth/me/delete/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# =============================================================================
# Token Refresh Tests
# =============================================================================

@pytest.mark.django_db
class TestTokenRefresh:
    """Functional tests for token refresh endpoint."""

    def test_token_refresh_success(self, api_client, user, tokens_for_user):
        """Test successful token refresh."""
        tokens = tokens_for_user(user)
        response = api_client.post('/api/auth/refresh', {
            'refresh': tokens['refresh']
        })
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data

    def test_token_refresh_invalid(self, api_client):
        """Test token refresh with invalid token fails."""
        response = api_client.post('/api/auth/refresh', {
            'refresh': 'invalid-token'
        })
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
