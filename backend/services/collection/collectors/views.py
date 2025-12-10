from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .serializers import (
    StartCollectionSerializer,
    MetricsFilterSerializer,
    CollectionPlanSerializer,
)
from .models import CollectionPlan, CollectedData
from .tasks import run_collection_in_background
import logging

logger = logging.getLogger(__name__)


class StartCollectionView(APIView):
    """
    Create a collection plan with repository details and token

    """
    
    def post(self, request):
        user_id = request.headers.get('X-User-ID')
        if not user_id:
            return Response(
                {'error': 'User ID required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        serializer = StartCollectionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        validated_data = serializer.validated_data
        
        logger.info(f"Collection plan initiated for: {validated_data['repository_full_name']}")
        
        # Create collection plan
        collection_plan = CollectionPlan.objects.create(
            user=int(user_id),
            workspace_id=validated_data['workspace_id'],
            repository_id=validated_data['repository_id'],
            repository_name=validated_data['repository_name'],
            repository_full_name=validated_data['repository_full_name'],
            platform=validated_data['platform'],
            repository_url=validated_data.get('repository_url'),
            default_branch=validated_data.get('default_branch'),
            token_encrypted=validated_data['token'],
            status='pending'
        )
        
        return Response({
            'success': True,
            'message': 'Collection plan created. Now select metrics and filters.',
            'collection_plan': CollectionPlanSerializer(collection_plan).data,
            'available_metrics': [
                {'value': 'pull_requests', 'label': 'Pull Requests / Merge Requests'},
                {'value': 'commits', 'label': 'Commits'},
                {'value': 'issues', 'label': 'Issues'},
                {'value': 'comments', 'label': 'Comments'},
                {'value': 'reviews', 'label': 'Reviews (GitHub only)'},
            ]
        }, status=status.HTTP_201_CREATED)


class ConfigureMetricsView(APIView):
    """
    Configure metrics and filters for a collection plan
    """
    
    def post(self, request, plan_id):
        user_id = request.headers.get('X-User-ID')
        if not user_id:
            return Response(
                {'error': 'User ID required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        collection_plan = get_object_or_404(
            CollectionPlan,
            id=plan_id,
            user=int(user_id)
        )
        
        if collection_plan.status != 'pending':
            return Response(
                {'error': 'Can only configure metrics for pending plans'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = MetricsFilterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        validated_data = serializer.validated_data
        
        # Update collection plan
        collection_plan.selected_metrics = validated_data['selected_metrics']
        collection_plan.filters = {
            'start_date': validated_data.get('start_date').isoformat() if validated_data.get('start_date') else None,
            'end_date': validated_data.get('end_date').isoformat() if validated_data.get('end_date') else None,
            'status': validated_data.get('status', []),
        }
        collection_plan.save()
        
        logger.info(f"Metrics configured for plan {plan_id}: {validated_data['selected_metrics']}")
        
        return Response({
            'success': True,
            'message': 'Metrics and filters configured successfully',
            'collection_plan': CollectionPlanSerializer(collection_plan).data
        })


class ValidateCollectionPlanView(APIView):
    """
    Show collection plan summary before starting collection
    """
    
    def get(self, request, plan_id):
        user_id = request.headers.get('X-User-ID')
        if not user_id:
            return Response(
                {'error': 'User ID required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        collection_plan = get_object_or_404(
            CollectionPlan,
            id=plan_id,
            user=int(user_id)
        )
        
        summary = {
            'collection_plan': CollectionPlanSerializer(collection_plan).data,
            'summary': {
                'repository': collection_plan.repository_full_name,
                'platform': collection_plan.platform,
                'metrics_count': len(collection_plan.selected_metrics),
                'metrics': collection_plan.selected_metrics,
                'filters': collection_plan.filters,
            }
        }
        
        return Response(summary)


class ExecuteCollectionView(APIView):
    """
    Start the actual data collection IN BACKGROUND
    """
    
    def post(self, request, plan_id):
        user_id = request.headers.get('X-User-ID')
        if not user_id:
            return Response(
                {'error': 'User ID required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        collection_plan = get_object_or_404(
            CollectionPlan,
            id=plan_id,
            user=int(user_id)
        )
        
        if collection_plan.status not in ['pending', 'failed']:
            return Response(
                {'error': f'Cannot start collection with status: {collection_plan.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not collection_plan.selected_metrics:
            return Response(
                {'error': 'No metrics selected. Configure metrics first.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Start collection in background
        run_collection_in_background(plan_id)
        
        return Response({
            'success': True,
            'message': 'Collection started in background',
            'collection_plan': CollectionPlanSerializer(collection_plan).data
        })


class CollectionStatusView(APIView):
    """
    Get the status of a collection
    """
    
    def get(self, request, plan_id):
        user_id = request.headers.get('X-User-ID')
        if not user_id:
            return Response(
                {'error': 'User ID required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        collection_plan = get_object_or_404(
            CollectionPlan,
            id=plan_id,
            user=int(user_id)
        )
        
        return Response({
            'collection_plan': CollectionPlanSerializer(collection_plan).data,
            'status': collection_plan.status,
            'progress_percentage': collection_plan.progress_percentage,
            'collected_items': collection_plan.collected_items,
            'total_items': collection_plan.total_items,
            'stats': collection_plan.stats,
        })


class CollectionPlanListView(APIView):
    """
    List all collection plans for a user
    """
    
    def get(self, request):
        user_id = request.headers.get('X-User-ID')
        if not user_id:
            return Response(
                {'error': 'User ID required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        plans = CollectionPlan.objects.filter(user=int(user_id))
        serializer = CollectionPlanSerializer(plans, many=True)
        
        return Response(serializer.data)


class CollectedDataView(APIView):
    """
    Get collected data for a collection plan
    """
    
    def get(self, request, plan_id):
        user_id = request.headers.get('X-User-ID')
        if not user_id:
            return Response(
                {'error': 'User ID required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        collection_plan = get_object_or_404(
            CollectionPlan,
            id=plan_id,
            user=int(user_id)
        )
        
        try:
            collected_data = CollectedData.objects.get(collection_plan=collection_plan)
            
            return Response({
                'collection_plan_id': plan_id,
                'raw_data': collected_data.raw_data,
                'stats': collection_plan.stats,
            })
        except CollectedData.DoesNotExist:
            return Response({
                'collection_plan_id': plan_id,
                'raw_data': {},
                'message': 'No data collected yet'
            })