from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    ChangePasswordView,
    DeleteUserView,
    RegisterView,
    LoginView,
    MeView,
    GitHubLoginView,
    GitHubCallbackView,
    GitLabLoginView,
    GitLabCallbackView,
    GoogleLoginView,
    GoogleCallbackView,
    IntrospectView,
    UpdateUserView,
)

urlpatterns = [
    path("register", RegisterView.as_view()),
    path("login", LoginView.as_view()),
    path("refresh", TokenRefreshView.as_view()),
    path("introspect", IntrospectView.as_view(), name="introspect"),
    path("me", MeView.as_view()),
    path("me/update/", UpdateUserView.as_view(), name="update_user"),
    path("me/change-password/", ChangePasswordView.as_view(), name="change_password"),
    path("me/delete/", DeleteUserView.as_view(), name="delete_user"),
    path("oauth/github", GitHubLoginView.as_view(), name="github_login"),
    path("oauth/github/callback", GitHubCallbackView.as_view(), name="github_callback"),
    path("oauth/gitlab", GitLabLoginView.as_view(), name="gitlab_login"),
    path("oauth/gitlab/callback", GitLabCallbackView.as_view(), name="gitlab_callback"),
    path("oauth/google", GoogleLoginView.as_view(), name="google_login"),
    path("oauth/google/callback", GoogleCallbackView.as_view(), name="google_callback"),
]
