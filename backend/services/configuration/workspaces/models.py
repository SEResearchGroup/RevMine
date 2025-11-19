from django.db import models
from .encryption import token_encryptor

class Workspace(models.Model):
    PLATFORM_CHOICES = [
        ('github', 'GitHub'),
        ('gitlab', 'GitLab.com'),
        ('gitlab_self', 'GitLab Self-Hosted'),
    ]

    user = models.IntegerField()
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True) 
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES)
    url = models.URLField(blank=True, null=True, help_text="Requis seulement pour GitLab self-hosted")
    token_encrypted = models.TextField()
    is_active = models.BooleanField(default=True)
    last_sync = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'config_workspaces'
        ordering = ['-created_at']
        unique_together = ['user', 'name']  # évite les doublons

    def set_token(self, raw_token: str):
        self.token_encrypted = token_encryptor.encrypt(raw_token)

    def get_token(self) -> str:
        return token_encryptor.decrypt(self.token_encrypted)

    def get_api_base_url(self) -> str:
        if self.platform == 'github':
            return 'https://api.github.com'
        elif self.platform == 'gitlab':
            return 'https://gitlab.com/api/v4'
        else:  # gitlab_self
            return f"{self.url.rstrip('/')}/api/v4"

    def __str__(self):
        return f"{self.name} ({self.platform}) - {self.user.username}"