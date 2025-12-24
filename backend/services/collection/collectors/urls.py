from django.urls import path
from .views import (
    StartCollectionView,
    GetBranchesView,
    ConfigureMetricsView,
    ValidateCollectionPlanView,
    ExecuteCollectionView,
    CollectionStatusView,
    CollectionPlanListView,
    CollectionHistoryView,
    CollectedDataView,
)

urlpatterns = [
    
    path('start/', StartCollectionView.as_view(), name='collection-start'),

   
    path('plans/<int:plan_id>/configure/', ConfigureMetricsView.as_view(), name='collection-configure'),
    
  
    path('plans/<int:plan_id>/validate/', ValidateCollectionPlanView.as_view(), name='collection-validate'),
    
   
    path('plans/<int:plan_id>/execute/', ExecuteCollectionView.as_view(), name='collection-execute'),

    
    path('plans/<int:plan_id>/branches/', GetBranchesView.as_view(), name='collection-branches'),
    

    path('plans/<int:plan_id>/status/', CollectionStatusView.as_view(), name='collection-status'),
    
   
    path('plans/<int:plan_id>/data/', CollectedDataView.as_view(), name='collection-data'),
    
    
    path('plans/', CollectionPlanListView.as_view(), name='collection-plans'),
    
   
    path('history/<int:repository_id>/', CollectionHistoryView.as_view(), name='collection-history'),
]