from rest_framework import serializers
from .models import User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'date_joined']

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        help_text="Password (minimum 8 characters recommended)"
    )

    first_name = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="First name"
    )
    last_name = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Last name"
    )

    class Meta:
        model = User
        fields = ['email', 'password', 'first_name', 'last_name']  

    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
        )
        user.first_name = validated_data.get('first_name', "")
        user.last_name = validated_data.get('last_name', "")
        user.save()
        return user

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(help_text="User's email address")
    password = serializers.CharField(
        write_only=True,
        help_text="Password"
    )

class LoginResponseSerializer(serializers.Serializer):
    """Serializer to document the login response"""
    access = serializers.CharField(help_text="JWT access token")
    refresh = serializers.CharField(help_text="JWT refresh token")
    user = UserSerializer(help_text="User information")

class OAuthUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'date_joined']
