from django.urls import path
from .views import (
    WorkspaceListCreateView,
    WorkspaceDetailView,
    WorkspaceTestConnectionView
)

urlpatterns = [
    path('workspaces/', WorkspaceListCreateView.as_view(), name='workspace-list-create'),    
    path('workspaces/test-connection/', WorkspaceTestConnectionView.as_view(), name='workspace-test-connection'),    
    path('workspaces/<int:workspace_id>/', WorkspaceDetailView.as_view(), name='workspace-detail'),    
    path('workspaces/<int:workspace_id>/test/', WorkspaceTestConnectionView.as_view(), name='workspace-test-existing'),
]