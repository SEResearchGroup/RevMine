from django.db import models
from .encryption import token_encryption


class Workspace(models.Model):
    PLATFORM_CHOICES = [
        ("github", "GitHub"),
        ("gitlab", "GitLab.com"),
        ("gitlab_self", "GitLab Self-Hosted"),
    ]

    user = models.IntegerField()
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES)
    url = models.URLField(
        blank=True, null=True, help_text="Required only for GitLab self-hosted"
    )
    token_encrypted = models.TextField()
    is_active = models.BooleanField(default=True)
    last_sync = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "config_workspaces"
        ordering = ["-created_at"]
        unique_together = ["user", "name"]

    def set_token(self, raw_token: str):
        self.token_encrypted = token_encryption.encrypt(raw_token)

    def get_token(self) -> str:
        return token_encryption.decrypt(self.token_encrypted)

    def get_api_base_url(self) -> str:
        if self.platform == "github":
            return "https://api.github.com"
        elif self.platform == "gitlab":
            return "https://gitlab.com/api/v4"
        else:  # gitlab_self
            return f"{self.url.rstrip('/')}/api/v4"

    def __str__(self):
        return f"{self.name} ({self.platform}) - User {self.user}"


class Repository(models.Model):
    """Unified model to store both GitHub and GitLab repositories"""

    workspace = models.ForeignKey(
        Workspace, on_delete=models.CASCADE, related_name="repositories"
    )

    external_id = models.CharField(
        max_length=100, help_text="ID of the repo on GitHub/GitLab"
    )

    name = models.CharField(max_length=255)
    full_name = models.CharField(max_length=500, help_text="Ex: owner/repo-name")
    description = models.TextField(blank=True, null=True)

    url = models.URLField(help_text="URL of the repository")
    web_url = models.URLField(help_text="Web URL to access the repository")

    owner = models.CharField(max_length=255)
    owner_type = models.CharField(
        max_length=50, blank=True, null=True, help_text="User, Organization, Group"
    )

    default_branch = models.CharField(max_length=100, default="main")
    language = models.CharField(max_length=50, blank=True, null=True)
    stars_count = models.IntegerField(default=0)
    forks_count = models.IntegerField(default=0)
    open_issues_count = models.IntegerField(default=0)

    is_private = models.BooleanField(default=False)
    is_fork = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)

    created_at_platform = models.DateTimeField(
        help_text="Creation date on the platform"
    )
    last_activity_at = models.DateTimeField(null=True, blank=True)

    is_active = models.BooleanField(
        default=True, help_text="If the repo is active for analysis"
    )
    last_analyzed_at = models.DateTimeField(null=True, blank=True)
    imported_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    raw_data = models.JSONField(
        blank=True, null=True, help_text="Raw data from the API"
    )

    class Meta:
        db_table = "repositories"
        ordering = ["-last_activity_at", "-created_at_platform"]
        unique_together = ["workspace", "external_id"]
        indexes = [
            models.Index(fields=["workspace", "is_active"]),
            models.Index(fields=["external_id"]),
            models.Index(fields=["full_name"]),
        ]

    def __str__(self):
        return f"{self.full_name} ({self.workspace.platform})"

    @property
    def platform(self):
        return self.workspace.platform
