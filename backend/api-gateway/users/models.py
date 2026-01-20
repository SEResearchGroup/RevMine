from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)

    first_name = models.CharField(max_length=150, blank=True, default="")
    last_name = models.CharField(max_length=150, blank=True, default="")
    position = models.CharField(max_length=100, blank=True, default="")

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

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []  

    class Meta:
        db_table = 'auth_users'
        unique_together = [['email', 'oauth_provider']]
