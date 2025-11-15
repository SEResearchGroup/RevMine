from django.db import models
from .encryption import token_encryptor

class Workspace(models.Model):
    PLATFORM_CHOICES = [
        ('github', 'GitHub'),
        ('gitlab', 'GitLab'),
        ('gitlab_self', 'GitLab Self-Hosted'),
    ]
    
    user_id = models.IntegerField() 
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES)
    url = models.URLField(blank=True, null=True)  
    token_encrypted = models.TextField()  
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_sync = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        db_table = 'config_workspaces'
        ordering = ['-created_at']
    
    def set_token(self, token):
        """Encrypt and store the token"""
        self.token_encrypted = token_encryptor.encrypt(token)
    
    def get_token(self):
        """Decrypt and return the token"""
        return token_encryptor.decrypt(self.token_encrypted)
    
    def get_api_url(self):
        """Return the API URL based on the platform"""
        if self.platform == 'github':
            return 'https://api.github.com'
        elif self.platform == 'gitlab':
            return 'https://gitlab.com/api/v4'
        else:  
            return f"{self.url.rstrip('/')}/api/v4"
    
    def __str__(self):
        return f"{self.name} ({self.platform})"