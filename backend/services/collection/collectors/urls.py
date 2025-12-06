from django.urls import path
from .views import StartCollectionView, CollectionPlanListView

urlpatterns = [
    path('start/', StartCollectionView.as_view(), name='collection-start'),
    path('plans/', CollectionPlanListView.as_view(), name='collection-plans'),
]