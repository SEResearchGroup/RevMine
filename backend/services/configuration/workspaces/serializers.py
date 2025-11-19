from rest_framework import serializers
from .models import Workspace
import requests

class WorkspaceSerializer(serializers.ModelSerializer):
    token = serializers.CharField(write_only=True, required=True)
    description = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Workspace
        fields = [
            'id', 'name', 'description', 'platform', 'url',
            'token', 'is_active', 'created_at', 'updated_at', 'last_sync'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'last_sync']

    def validate(self, data):
        platform = data['platform']
        url = data.get('url')

        if platform == 'gitlab_self' and not url:
            raise serializers.ValidationError({"url": "L'URL est obligatoire pour GitLab self-hosted."})

        if platform in ('github', 'gitlab') and url:
            raise serializers.ValidationError({"url": "L'URL ne doit pas être fournie pour GitHub ou GitLab.com."})

        return data


class WorkspaceListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workspace
        fields = ['id', 'name', 'description', 'platform', 'url', 'is_active', 'created_at', 'updated_at', 'last_sync']


class TestConnectionSerializer(serializers.Serializer):
    platform = serializers.ChoiceField(choices=[choice[0] for choice in Workspace.PLATFORM_CHOICES])
    url = serializers.URLField(required=False, allow_blank=True)
    token = serializers.CharField()

    def validate(self, data):
        platform = data['platform']
        if platform == 'gitlab_self' and not data.get('url'):
            raise serializers.ValidationError({"url": "URL requise pour GitLab self-hosted"})
        return data