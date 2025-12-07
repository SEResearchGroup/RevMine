from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models

class UserManager(BaseUserManager):
    def create_user(self, email, password=None):
        if not email:
            raise ValueError('Invalid email address')
        user = self.model(email=self.normalize_email(email))
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password):
        user = self.create_user(email, password)
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user

class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField()  
    first_name = models.CharField(max_length=150, blank=True, default="")
    last_name = models.CharField(max_length=150, blank=True, default="")
    position = models.CharField(max_length=100, blank=True, default="")
    
    # Champs pour identifier le provider OAuth
    oauth_provider = models.CharField(
        max_length=20, 
        blank=True, 
        null=True,
        choices=[
            ('github', 'GitHub'),
            ('gitlab', 'GitLab'),
            ('google', 'Google'),
        ]
    )
    oauth_id = models.CharField(max_length=255, blank=True, null=True)
    
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = 'id'
    REQUIRED_FIELDS = ['email', 'password']
    
    class Meta:
        db_table = 'auth_users'
        unique_together = [['email', 'oauth_provider']]