"""
backend/services/collection/collectors/views.py
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .serializers import (
    StartCollectionSerializer,
    MetricsFilterSerializer,
    CollectionPlanSerializer,
    CollectedDataSerializer
)
from .models import CollectionPlan, CollectedData
from .collector import DataCollector
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
        
        # Print project details
        print("\n" + "="*80)
        print("🚀 COLLECTION SERVICE - PROJECT DETAILS RECEIVED")
        print("="*80)
        print(f"👤 User ID: {user_id}")
        print(f"📦 Repository ID: {validated_data['repository_id']}")
        print(f"🏢 Workspace ID: {validated_data['workspace_id']}")
        print(f"📂 Repository Name: {validated_data['repository_name']}")
        print(f"📋 Full Name: {validated_data['repository_full_name']}")
        print(f"🔧 Platform: {validated_data['platform']}")
        if 'repository_url' in validated_data:
            print(f"🔗 URL: {validated_data['repository_url']}")
        if 'default_branch' in validated_data:
            print(f"🌿 Default Branch: {validated_data['default_branch']}")
        print(f"🔑 Token received: ✓")
        print("="*80 + "\n")
        
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
            token_encrypted=validated_data['token'],  # Store token directly for now
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
        
        # Get collection plan
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
        
        # Validate metrics and filters
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
        
        # Prepare summary
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
    Start the actual data collection
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
        
        # Start collection
        collection_plan.status = 'in_progress'
        collection_plan.started_at = timezone.now()
        collection_plan.error_message = None
        collection_plan.save()
        
        logger.info(f"Starting collection for plan {plan_id}")
        
        try:
            # Initialize collector
            collector = DataCollector(
                platform=collection_plan.platform,
                token=collection_plan.token_encrypted,
                repo_full_name=collection_plan.repository_full_name
            )
            
            # Prepare filters
            filters = collection_plan.filters.copy()
            if filters.get('start_date'):
                from datetime import date
                filters['start_date'] = date.fromisoformat(filters['start_date'])
            if filters.get('end_date'):
                from datetime import date
                filters['end_date'] = date.fromisoformat(filters['end_date'])
            
            total_collected = 0
            
            # Collect each metric
            for metric in collection_plan.selected_metrics:
                print(f"\n📊 Collecting {metric}...")
                
                data = collector.collect_metric(metric, filters)
                
                print(f"✅ Collected {len(data)} items for {metric}")
                
                # Store collected data
                for item in data:
                    external_id = str(item.get('id') or item.get('number') or item.get('sha', ''))
                    
                    CollectedData.objects.update_or_create(
                        collection_plan=collection_plan,
                        metric_type=metric,
                        external_id=external_id,
                        defaults={'raw_data': item}
                    )
                    
                    total_collected += 1
                    
                    # Update progress
                    collection_plan.collected_items = total_collected
                    collection_plan.save()
            
            # Mark as completed
            collection_plan.status = 'completed'
            collection_plan.completed_at = timezone.now()
            collection_plan.total_items = total_collected
            collection_plan.save()
            
            print(f"\n🎉 Collection completed! Total items: {total_collected}\n")
            
            return Response({
                'success': True,
                'message': 'Collection completed successfully',
                'collection_plan': CollectionPlanSerializer(collection_plan).data,
                'total_collected': total_collected
            })
        
        except Exception as e:
            logger.error(f"Collection failed: {e}")
            
            collection_plan.status = 'failed'
            collection_plan.error_message = str(e)
            collection_plan.save()
            
            return Response({
                'success': False,
                'error': 'Collection failed',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
        
        # Get metric type from query params
        metric_type = request.query_params.get('metric_type')
        
        collected_data = CollectedData.objects.filter(collection_plan=collection_plan)
        
        if metric_type:
            collected_data = collected_data.filter(metric_type=metric_type)
        
        serializer = CollectedDataSerializer(collected_data, many=True)
        
        return Response({
            'collection_plan_id': plan_id,
            'total_items': collected_data.count(),
            'data': serializer.data
        })