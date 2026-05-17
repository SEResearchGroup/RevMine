"""
Unit and Functional Tests for API Gateway Users App.
Tests cover authentication, user management, and authorization flows.
"""
import pytest
import requests
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from django.contrib.auth import get_user_model

User = get_user_model()


class OAuthResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload


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


@pytest.mark.django_db
class TestTokenIntrospection:
    """Functional tests for gateway token introspection."""

    def test_introspect_valid_token(self, api_client, user, tokens_for_user):
        tokens = tokens_for_user(user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

        response = api_client.post("/api/auth/introspect")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["active"] is True
        assert response.data["user_id"] == user.id

    def test_introspect_missing_token(self, api_client):
        response = api_client.post("/api/auth/introspect")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data == {"active": False}


@pytest.mark.django_db
class TestOAuthFlows:
    """OAuth endpoints are unit-tested with provider calls mocked."""

    @override_settings(
        GITHUB_CLIENT_ID="github-client",
        GITHUB_REDIRECT_URI="https://frontend.example/auth/github/callback",
        GITLAB_CLIENT_ID="gitlab-client",
        GITLAB_REDIRECT_URI="https://frontend.example/auth/gitlab/callback",
        GOOGLE_CLIENT_ID="google-client",
        GOOGLE_REDIRECT_URI="https://frontend.example/auth/google/callback",
    )
    @pytest.mark.parametrize(
        ("path", "expected_provider_url", "client_id"),
        [
            ("/api/auth/oauth/github", "https://github.com/login/oauth/authorize", "github-client"),
            ("/api/auth/oauth/gitlab", "https://gitlab.com/oauth/authorize", "gitlab-client"),
            ("/api/auth/oauth/google", "https://accounts.google.com/o/oauth2/v2/auth", "google-client"),
        ],
    )
    def test_login_urls(self, api_client, path, expected_provider_url, client_id):
        response = api_client.get(path)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["url"].startswith(expected_provider_url)
        assert f"client_id={client_id}" in response.data["url"]

    @pytest.mark.parametrize(
        "path",
        [
            "/api/auth/oauth/github/callback",
            "/api/auth/oauth/gitlab/callback",
            "/api/auth/oauth/google/callback",
        ],
    )
    def test_callback_requires_code(self, api_client, path):
        response = api_client.get(path)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"] == "No code provided"

    @override_settings(
        GITHUB_CLIENT_ID="github-client",
        GITHUB_CLIENT_SECRET="github-secret",
        GITHUB_REDIRECT_URI="https://frontend.example/auth/github/callback",
    )
    def test_github_callback_creates_user_from_primary_email(self, api_client, monkeypatch):
        monkeypatch.setattr(
            "users.views.requests.post",
            lambda *args, **kwargs: OAuthResponse(payload={"access_token": "provider-token"}),
        )
        provider_responses = iter(
            [
                OAuthResponse(payload={"id": 10, "name": "Ada Lovelace", "email": None}),
                OAuthResponse(payload=[{"email": "ada@example.com", "primary": True}]),
            ]
        )
        monkeypatch.setattr(
            "users.views.requests.get",
            lambda *args, **kwargs: next(provider_responses),
        )

        response = api_client.get("/api/auth/oauth/github/callback", {"code": "oauth-code"})

        assert response.status_code == status.HTTP_200_OK
        assert response.data["user"]["email"] == "ada@example.com"
        user = User.objects.get(oauth_provider="github", oauth_id="10")
        assert user.first_name == "Ada"
        assert user.last_name == "Lovelace"

    @override_settings(
        GITLAB_CLIENT_ID="gitlab-client",
        GITLAB_CLIENT_SECRET="gitlab-secret",
        GITLAB_REDIRECT_URI="https://frontend.example/auth/gitlab/callback",
    )
    def test_gitlab_callback_creates_user(self, api_client, monkeypatch):
        monkeypatch.setattr(
            "users.views.requests.post",
            lambda *args, **kwargs: OAuthResponse(payload={"access_token": "provider-token"}),
        )
        monkeypatch.setattr(
            "users.views.requests.get",
            lambda *args, **kwargs: OAuthResponse(
                payload={
                    "id": 20,
                    "name": "Grace Hopper",
                    "email": "grace@example.com",
                }
            ),
        )

        response = api_client.get("/api/auth/oauth/gitlab/callback", {"code": "oauth-code"})

        assert response.status_code == status.HTTP_200_OK
        assert response.data["user"]["email"] == "grace@example.com"
        user = User.objects.get(oauth_provider="gitlab", oauth_id="20")
        assert user.first_name == "Grace"
        assert user.last_name == "Hopper"

    @override_settings(
        GOOGLE_CLIENT_ID="google-client",
        GOOGLE_CLIENT_SECRET="google-secret",
        GOOGLE_REDIRECT_URI="https://frontend.example/auth/google/callback",
    )
    def test_google_callback_creates_user(self, api_client, monkeypatch):
        monkeypatch.setattr(
            "users.views.requests.post",
            lambda *args, **kwargs: OAuthResponse(payload={"access_token": "provider-token"}),
        )
        monkeypatch.setattr(
            "users.views.requests.get",
            lambda *args, **kwargs: OAuthResponse(
                payload={
                    "id": "google-30",
                    "email": "katherine@example.com",
                    "given_name": "Katherine",
                    "family_name": "Johnson",
                }
            ),
        )

        response = api_client.get("/api/auth/oauth/google/callback", {"code": "oauth-code"})

        assert response.status_code == status.HTTP_200_OK
        assert response.data["user"]["email"] == "katherine@example.com"
        user = User.objects.get(oauth_provider="google", oauth_id="google-30")
        assert user.first_name == "Katherine"
        assert user.last_name == "Johnson"

    def test_github_callback_handles_provider_network_error(self, api_client, monkeypatch):
        def raise_network_error(*args, **kwargs):
            raise requests.RequestException("provider unavailable")

        monkeypatch.setattr(
            "users.views.requests.post",
            raise_network_error,
        )

        response = api_client.get("/api/auth/oauth/github/callback", {"code": "oauth-code"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"].startswith("Network error:")
