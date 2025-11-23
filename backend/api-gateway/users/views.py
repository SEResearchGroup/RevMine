from rest_framework import status, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample
from drf_spectacular.types import OpenApiTypes
from rest_framework import serializers
from .serializers import RegisterSerializer, LoginSerializer, UserSerializer

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
                'password': 'password123'
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