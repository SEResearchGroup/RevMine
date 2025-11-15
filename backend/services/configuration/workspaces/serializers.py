from rest_framework import serializers
from .models import Workspace
import requests

class WorkspaceSerializer(serializers.ModelSerializer):
    token = serializers.CharField(write_only=True)
    
    class Meta:
        model = Workspace
        fields = ['id', 'name', 'description', 'platform', 'url', 'token', 'is_active', 
                  'created_at', 'updated_at', 'last_sync']
        read_only_fields = ['id', 'created_at', 'updated_at', 'last_sync']
    
    def validate(self, data):
        """Validate data based on platform"""
        platform = data.get('platform')
        url = data.get('url')
        
        # GitLab self-hosted requires a URL
        if platform == 'gitlab_self' and not url:
            raise serializers.ValidationError({
                'url': 'URL required for self-hosted GitLab'
            })
        
        # GitHub and GitLab.com should not have a URL
        if platform in ['github', 'gitlab'] and url:
            raise serializers.ValidationError({
                'url': 'URL not needed for this platform'
            })
        
        return data
    
    def create(self, validated_data):
        token = validated_data.pop('token')
        user_id = self.context['request'].user.id
        
        workspace = Workspace(**validated_data)
        workspace.user_id = user_id
        workspace.set_token(token)
        workspace.save()
        
        return workspace
    
    def update(self, instance, validated_data):
        token = validated_data.pop('token', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        if token:
            instance.set_token(token)
        
        instance.save()
        return instance

class WorkspaceListSerializer(serializers.ModelSerializer):
    """Serializer for the list (without token)"""
    class Meta:
        model = Workspace
        fields = ['id', 'name', 'description', 'platform', 'url', 'is_active', 
                  'created_at', 'updated_at', 'last_sync']

class TestConnectionSerializer(serializers.Serializer):
    """To test the connection"""
    platform = serializers.ChoiceField(choices=Workspace.PLATFORM_CHOICES)
    url = serializers.URLField(required=False, allow_blank=True)
    token = serializers.CharField()
    
    def validate_token_connection(self):
        """Test the connection with the credentials"""
        platform = self.validated_data['platform']
        token = self.validated_data['token']
        url = self.validated_data.get('url', '')
        
        try:
            if platform == 'github':
                response = requests.get(
                    'https://api.github.com/user',
                    headers={'Authorization': f'token {token}'},
                    timeout=10
                )
            else:  # gitlab or gitlab_self
                api_url = url.rstrip('/') + '/api/v4' if url else 'https://gitlab.com/api/v4'
                response = requests.get(
                    f'{api_url}/user',
                    headers={'PRIVATE-TOKEN': token},
                    timeout=10
                )
            
            if response.status_code == 200:
                return {'status': 'success', 'user': response.json()}
            else:
                return {'status': 'error', 'message': 'Invalid credentials'}
                
        except requests.RequestException as e:
            return {'status': 'error', 'message': str(e)}