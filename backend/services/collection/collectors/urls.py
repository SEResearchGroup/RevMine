"""
backend/services/collection/collectors/urls.py
"""
from django.urls import path
from .views import (
    StartCollectionView,
    ConfigureMetricsView,
    ValidateCollectionPlanView,
    ExecuteCollectionView,
    CollectionStatusView,
    CollectionPlanListView,
    CollectedDataView,
)

urlpatterns = [
    # Step 1: Create collection plan
    path('start/', StartCollectionView.as_view(), name='collection-start'),
    
    # Step 2: Configure metrics and filters
    path('plans/<int:plan_id>/configure/', ConfigureMetricsView.as_view(), name='collection-configure'),
    
    # Step 3: Validate and review plan
    path('plans/<int:plan_id>/validate/', ValidateCollectionPlanView.as_view(), name='collection-validate'),
    
    # Step 4: Execute collection
    path('plans/<int:plan_id>/execute/', ExecuteCollectionView.as_view(), name='collection-execute'),
    
    # Get collection status
    path('plans/<int:plan_id>/status/', CollectionStatusView.as_view(), name='collection-status'),
    
    # Get collected data
    path('plans/<int:plan_id>/data/', CollectedDataView.as_view(), name='collection-data'),
    
    # List all plans
    path('plans/', CollectionPlanListView.as_view(), name='collection-plans'),
]