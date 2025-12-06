from rest_framework import status, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, get_user_model
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample
from drf_spectacular.types import OpenApiTypes
from rest_framework import serializers
from .serializers import RegisterSerializer, LoginSerializer, UserSerializer
import requests
from django.shortcuts import redirect
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes


class RegisterView(generics.CreateAPIView):
    """
    Create a new user account
    """
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer
    
    @extend_schema(
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

    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

class LoginResponseSerializer(serializers.Serializer):
    access = serializers.CharField(help_text="JWT access token")
    refresh = serializers.CharField(help_text="JWT refresh token")
    user = UserSerializer(help_text="Authenticated user information")


class LoginView(APIView):
    """
    User authentication
    """
    permission_classes = [AllowAny]

    @extend_schema(
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
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = authenticate(
            email=serializer.validated_data['email'],
            password=serializer.validated_data['password']
        )
        
        if user:
            refresh = RefreshToken.for_user(user)
            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': UserSerializer(user).data
            })
        return Response({'error': 'Invalid credentials'}, 
                   status=status.HTTP_401_UNAUTHORIZED)


class MeView(generics.RetrieveAPIView):
    """
    Retrieve the authenticated user's information
    """
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    @extend_schema(
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
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_object(self):
        return self.request.user
    

User = get_user_model()

class GitHubLoginView(APIView):
    """
    Initiate GitHub OAuth flow
    """
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="GitHub OAuth Login",
        description="Redirects to GitHub for OAuth authentication",
        responses={302: OpenApiResponse(description='Redirect to GitHub')},
        tags=['OAuth']
    )
    def get(self, request):
        github_auth_url = (
            f"https://github.com/login/oauth/authorize"
            f"?client_id={settings.GITHUB_CLIENT_ID}"
            f"&redirect_uri={settings.GITHUB_REDIRECT_URI}"
            f"&scope=user:email,read:user"
        )
        return Response({'url': github_auth_url})


class GitHubCallbackView(APIView):
    """
    Handle GitHub OAuth callback
    """
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="GitHub OAuth Callback",
        description="Handles the callback from GitHub OAuth",
        responses={
            200: LoginResponseSerializer,
            400: OpenApiResponse(description='OAuth error'),
        },
        tags=['OAuth']
    )
    def get(self, request):
        code = request.GET.get('code')
        
        if not code:
            print("No code provided in GitHub callback")
            return Response({'error': 'No code provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Exchange code for access token
        token_response = requests.post(
            'https://github.com/login/oauth/access_token',
            data={
                'client_id': settings.GITHUB_CLIENT_ID,
                'client_secret': settings.GITHUB_CLIENT_SECRET,
                'code': code,
                'redirect_uri': settings.GITHUB_REDIRECT_URI,
            },
            headers={'Accept': 'application/json'}
        )
        
        if token_response.status_code != 200:
            return Response({'error': 'Failed to get access token'}, status=status.HTTP_400_BAD_REQUEST)
        
        token_data = token_response.json()
        access_token = token_data.get('access_token')
        
        # Get user info from GitHub
        user_response = requests.get(
            'https://api.github.com/user',
            headers={
                'Authorization': f'Bearer {access_token}',
                'Accept': 'application/json'
            }
        )
        
        if user_response.status_code != 200:
            return Response({'error': 'Failed to get user info'}, status=status.HTTP_400_BAD_REQUEST)
        
        user_data = user_response.json()
        
        email = user_data.get('email')
        if not email:
            email_response = requests.get(
                'https://api.github.com/user/emails',
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'Accept': 'application/json'
                }
            )
            if email_response.status_code == 200:
                emails = email_response.json()
                primary_email = next((e for e in emails if e['primary']), None)
                email = primary_email['email'] if primary_email else emails[0]['email']
        print("creating or getting user with email:", email)
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                # 'username': user_data.get('login', email.split('@')[0]),
                'first_name': user_data.get('name', '').split()[0] if user_data.get('name') else '',
                'last_name': ' '.join(user_data.get('name', '').split()[1:]) if user_data.get('name') and len(user_data.get('name', '').split()) > 1 else '',
            }
            # defaults={}
        )
        
        user.github_token = access_token
        user.save()
        
        refresh = RefreshToken.for_user(user)
        print("GitHub OAuth successful for user:", user.email)  
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user).data
        })


class GitLabLoginView(APIView):
    """
    Initiate GitLab OAuth flow
    """
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="GitLab OAuth Login",
        description="Redirects to GitLab for OAuth authentication",
        responses={302: OpenApiResponse(description='Redirect to GitLab')},
        tags=['OAuth']
    )
    def get(self, request):
        gitlab_auth_url = (
            f"https://gitlab.com/oauth/authorize"
            f"?client_id={settings.GITLAB_CLIENT_ID}"
            f"&redirect_uri={settings.GITLAB_REDIRECT_URI}"
            f"&response_type=code"
            f"&scope=read_user+read_api"
        )
        return Response({'url': gitlab_auth_url})


class GitLabCallbackView(APIView):
    """
    Handle GitLab OAuth callback
    """
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="GitLab OAuth Callback",
        description="Handles the callback from GitLab OAuth",
        responses={
            200: LoginResponseSerializer,
            400: OpenApiResponse(description='OAuth error'),
        },
        tags=['OAuth']
    )
    def get(self, request):
        code = request.GET.get('code')
        
        if not code:
            return Response({'error': 'No code provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Exchange code for access token
        token_response = requests.post(
            'https://gitlab.com/oauth/token',
            data={
                'client_id': settings.GITLAB_CLIENT_ID,
                'client_secret': settings.GITLAB_CLIENT_SECRET,
                'code': code,
                'grant_type': 'authorization_code',
                'redirect_uri': settings.GITLAB_REDIRECT_URI,
            }
        )
        
        if token_response.status_code != 200:
            return Response({'error': 'Failed to get access token'}, status=status.HTTP_400_BAD_REQUEST)
        
        token_data = token_response.json()
        access_token = token_data.get('access_token')
        
        # Get user info from GitLab
        user_response = requests.get(
            'https://gitlab.com/api/v4/user',
            headers={
                'Authorization': f'Bearer {access_token}'
            }
        )
        
        if user_response.status_code != 200:
            return Response({'error': 'Failed to get user info'}, status=status.HTTP_400_BAD_REQUEST)
        
        user_data = user_response.json()
        email = user_data.get('email')
        
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                # 'username': user_data.get('username', email.split('@')[0]),
                'first_name': user_data.get('name', '').split()[0] if user_data.get('name') else '',
                'last_name': ' '.join(user_data.get('name', '').split()[1:]) if user_data.get('name') and len(user_data.get('name', '').split()) > 1 else '',
            }
        )
        
        user.gitlab_token = access_token
        user.save()
        
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user).data
        })
