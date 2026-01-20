from rest_framework import serializers
from .models import User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'position', 'last_name', 'date_joined']

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
    position = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Position or job title"
    )

    class Meta:
        model = User
        fields = ['email', 'password', 'first_name', 'last_name', 'position']  

    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
        )
        user.first_name = validated_data.get('first_name', "")
        user.last_name = validated_data.get('last_name', "")
        user.position = validated_data.get('position', "")
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
        fields = ['id', 'email', 'first_name', 'position', 'last_name', 'date_joined']

class UpdateUserSerializer(serializers.ModelSerializer):
    """Serializer for updating user data"""
    email = serializers.EmailField(
        required=False,
        help_text="Email address"
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
    position = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Position or job title"
    )

    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'position']

    def validate_email(self, value):
        """Verify that the email is not already used by another user"""
        user = self.context['request'].user
        if User.objects.exclude(pk=user.pk).filter(email=value).exists():
            raise serializers.ValidationError("This email is already in use.")
        return value

    def update(self, instance, validated_data):
        """Update the user"""
        instance.email = validated_data.get('email', instance.email)
        instance.first_name = validated_data.get('first_name', instance.first_name)
        instance.last_name = validated_data.get('last_name', instance.last_name)
        instance.position = validated_data.get('position', instance.position)
        instance.save()
        return instance


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for changing the password"""
    old_password = serializers.CharField(
        write_only=True,
        required=True,
        help_text="Current password"
    )
    new_password = serializers.CharField(
        write_only=True,
        required=True,
        help_text="New password (minimum 8 characters recommended)"
    )
    new_password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        help_text="Confirm new password"
    )

    def validate_old_password(self, value):
        """Verify that the old password is correct"""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value

    def validate(self, data):
        """Verify that the new passwords match"""
        if data['new_password'] != data['new_password_confirm']:
            raise serializers.ValidationError({
                "new_password_confirm": "Password fields didn't match."
            })
        return data

    def save(self):
        """Update the password"""
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user

