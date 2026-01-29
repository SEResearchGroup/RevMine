from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample
from .serializers import RegisterSerializer, LoginSerializer, UserSerializer, LoginResponseSerializer


register_view_schema = extend_schema(
    summary="Register a new user",
    description="Creates a new user account with email and password",
    request=RegisterSerializer,
    responses={
        201: RegisterSerializer,
        400: OpenApiResponse(description='Invalid data'),
    },
    examples=[
        OpenApiExample(
            'Registration example',
            value={
                'email': 'user@example.com',
                'password': 'password123',
                'first_name': 'John',
                'last_name': 'Doe'
            },
            request_only=True,
        ),
    ],
    tags=['Authentication']
)


login_view_schema = extend_schema(
    summary="User login",
    description="Authenticates a user with email and password and returns JWT tokens",
    request=LoginSerializer,
    responses={
        200: LoginResponseSerializer,
        401: OpenApiResponse(description='Invalid credentials'),
    },
    examples=[
        OpenApiExample(
            'Login example',
            value={
                'email': 'user@example.com',
                'password': 'password123'
            },
            request_only=True,
        ),
        OpenApiExample(
            'Successful response',
            value={
                'access': 'eyJ0eXAiOiJKV1QiLCJhbGc...',
                'refresh': 'eyJ0eXAiOiJKV1QiLCJhbGc...',
                'user': {
                    'id': 1,
                    'email': 'user@example.com',
                    'date_joined': '2024-01-01T00:00:00Z'
                }
            },
            response_only=True,
            status_codes=['200']
        ),
    ],
    tags=['Authentication']
)


me_view_schema = extend_schema(
    summary="User profile",
    description="Returns the information of the currently authenticated user",
    responses={
        200: UserSerializer,
        401: OpenApiResponse(description='Unauthenticated - Missing or invalid token'),
    },
    examples=[
        OpenApiExample(
            'User profile response',
            value={
                'id': 1,
                'email': 'user@example.com',
                'first_name': 'John',
                'last_name': 'Doe',
                'date_joined': '2024-01-01T00:00:00Z'
            },
            response_only=True,
        ),
    ],
    tags=['User']
)


github_login_schema = extend_schema(
    summary="GitHub OAuth Login",
    description="Redirects to GitHub for OAuth authentication",
    responses={302: OpenApiResponse(description='Redirect to GitHub')},
    tags=['OAuth']
)


github_callback_schema = extend_schema(
    summary="GitHub OAuth Callback",
    description="Handles the callback from GitHub OAuth",
    responses={
        200: LoginResponseSerializer,
        400: OpenApiResponse(description='OAuth error'),
    },
    tags=['OAuth']
)


gitlab_login_schema = extend_schema(
    summary="GitLab OAuth Login",
    description="Redirects to GitLab for OAuth authentication",
    responses={302: OpenApiResponse(description='Redirect to GitLab')},
    tags=['OAuth']
)


gitlab_callback_schema = extend_schema(
    summary="GitLab OAuth Callback",
    description="Handles the callback from GitLab OAuth",
    responses={
        200: LoginResponseSerializer,
        400: OpenApiResponse(description='OAuth error'),
    },
    tags=['OAuth']
)


google_login_schema = extend_schema(
    summary="Google OAuth Login",
    description="Redirects to Google for OAuth authentication",
    responses={302: OpenApiResponse(description='Redirect to Google')},
    tags=['OAuth']
)


google_callback_schema = extend_schema(
    summary="Google OAuth Callback",
    description="Handles the callback from Google OAuth",
    responses={
        200: LoginResponseSerializer,
        400: OpenApiResponse(description='OAuth error'),
    },
    tags=['OAuth']
)
