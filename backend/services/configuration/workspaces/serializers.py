from rest_framework import serializers
from .models import Workspace, Repository


class WorkspaceSerializer(serializers.ModelSerializer):
    """Serializer for workspace list view"""

    token = serializers.CharField(write_only=True, required=True)
    description = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Workspace
        fields = [
            "id",
            "name",
            "description",
            "platform",
            "url",
            "token",
            "is_active",
            "created_at",
            "updated_at",
            "last_sync",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "last_sync"]

    def get_token(self, obj):
        """Get decrypted token"""
        return obj.get_token()

    def validate_platform(self, value):
        """Validate platform choice"""
        valid_platforms = ["github", "gitlab", "gitlab_self"]
        if value not in valid_platforms:
            raise serializers.ValidationError(
                f"Platform must be one of: {valid_platforms}"
            )
        return value
    
    def validate(self, data):
        # For partial updates, get platform from instance if not provided
        platform = data.get('platform')
        if platform is None and self.instance:
            platform = self.instance.platform
        
        # Skip validation if platform is still unknown (shouldn't happen normally)
        if platform is None:
            return data
            
        url = data.get('url')
        # For partial updates, get url from instance if not in data
        if url is None and self.instance:
            url = self.instance.url

        if platform == "gitlab_self" and not url:
            raise serializers.ValidationError(
                {"url": "URL is required for GitLab self-hosted."}
            )

        if platform in ("github", "gitlab") and url:
            raise serializers.ValidationError(
                {"url": "URL should be empty for GitHub and GitLab.com."}
            )

        return data


class WorkspaceListSerializer(serializers.ModelSerializer):
    """Serializer for workspace detail view"""

    class Meta:
        model = Workspace
        fields = [
            "id",
            "name",
            "description",
            "platform",
            "url",
            "is_active",
            "created_at",
            "updated_at",
            "last_sync",
        ]


class TestConnectionSerializer(serializers.Serializer):
    """Serializer for testing Git API connections"""

    platform = serializers.ChoiceField(
        choices=[choice[0] for choice in Workspace.PLATFORM_CHOICES]
    )
    url = serializers.URLField(required=False, allow_blank=True)
    token = serializers.CharField()

    def validate(self, data):
        platform = data["platform"]
        if platform == "gitlab_self" and not data.get("url"):
            raise serializers.ValidationError(
                {"url": "URL is required for GitLab self-hosted."}
            )
        return data


class RepositorySerializer(serializers.ModelSerializer):
    platform = serializers.CharField(source="workspace.platform", read_only=True)
    workspace_name = serializers.CharField(source="workspace.name", read_only=True)

    class Meta:
        model = Repository
        fields = [
            "id",
            "workspace",
            "workspace_name",
            "platform",
            "external_id",
            "name",
            "full_name",
            "description",
            "url",
            "web_url",
            "owner",
            "owner_type",
            "default_branch",
            "language",
            "stars_count",
            "forks_count",
            "open_issues_count",
            "is_private",
            "is_fork",
            "is_archived",
            "is_active",
            "created_at_platform",
            "last_activity_at",
            "last_analyzed_at",
            "imported_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "external_id",
            "imported_at",
            "updated_at",
            "last_analyzed_at",
        ]


class RepositoryMinimalSerializer(serializers.ModelSerializer):
    """Lightweight version for lists"""

    platform = serializers.CharField(source="workspace.platform", read_only=True)

    class Meta:
        model = Repository
        fields = [
            "id",
            "name",
            "full_name",
            "platform",
            "is_active",
            "last_activity_at",
        ]
