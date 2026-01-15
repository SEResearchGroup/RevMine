from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.http import HttpResponse, FileResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .serializers import (
    StartCollectionSerializer,
    MetricsFilterSerializer,
    CollectionSerializer,
    CleanedDataSerializer,
    CreateCleanedDataSerializer,
)
from .models import Collection, CleanedData
from .tasks import run_collection_in_background
from .branch_fetcher import BranchFetcher
from .metrics_config import get_metrics_for_platform
from .minio_client import MinIOClient
from .csv_generator import CSVGenerator, StatisticsCSVGenerator
from datetime import datetime
import logging
import json
import io

logger = logging.getLogger(__name__)


class GetAvailableMetricsView(APIView):
    """
    Get available metrics for a platform WITHOUT creating a collection.
    This endpoint should be called when the user opens the project detail page.
    """

    def get(self, request):
        user_id = request.headers.get('X-User-ID')
        if not user_id:
            return Response(
                {'error': 'User ID required'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        platform = request.query_params.get('platform', 'github')
        repository_id = request.query_params.get('repository_id')
        
        if not repository_id:
            return Response(
                {'error': 'repository_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if there's an existing active collection for this repository
        existing_collection = Collection.get_active_for_repository(
            user_id=int(user_id),
            repository_id=int(repository_id)
        )

        available_metrics = get_metrics_for_platform(platform)

        response_data = {
            'success': True,
            'available_metrics': available_metrics,
            'platform': platform,
            'has_active_collection': existing_collection is not None,
        }

        if existing_collection:
            response_data['active_collection'] = CollectionSerializer(existing_collection).data

        return Response(response_data)


class GetBranchesForRepositoryView(APIView):
    """
    Get branches for a repository using provided token.
    Does NOT require a collection to exist.
    """

    def post(self, request):
        user_id = request.headers.get('X-User-ID')
        if not user_id:
            return Response(
                {'error': 'User ID required'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        platform = request.data.get('platform')
        token = request.data.get('token')
        repo_full_name = request.data.get('repository_full_name')
        default_branch = request.data.get('default_branch')

        if not all([platform, token, repo_full_name]):
            return Response(
                {'error': 'platform, token, and repository_full_name are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            branch_fetcher = BranchFetcher(
                platform=platform,
                token=token,
                repo_full_name=repo_full_name
            )

            branches = branch_fetcher.fetch_branches()

            return Response({
                'success': True,
                'branches': branches,
                'default_branch': default_branch
            })

        except Exception as e:
            logger.error(f"Error fetching branches: {e}")
            return Response({
                'success': False,
                'error': str(e),
                'branches': []
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class StartCollectionView(APIView):
    """
    Create or retrieve a collection for a repository.
    
    This endpoint is IDEMPOTENT - if an active collection already exists
    for the user/repository, it returns that instead of creating a new one.
    This prevents duplicate collections from being created on page reloads.
    """

    @transaction.atomic
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
        repository_id = validated_data['repository_id']
        platform = validated_data['platform']
        user_id_int = int(user_id)

        # Check for ANY active (non-completed, non-failed) collection
        # This prevents duplicates when user re-enters the page
        existing_collection = Collection.get_active_for_repository(
            user_id=user_id_int,
            repository_id=repository_id
        )

        if existing_collection:
            # If the existing collection is in_progress but likely orphaned (stale),
            # mark it as paused so user can start a new one
            if existing_collection.status == 'in_progress':
                from django.utils import timezone
                from datetime import timedelta
                
                # Consider a collection orphaned if it hasn't been updated in 5 minutes
                # This handles cases where container stopped or network disconnected
                stale_threshold = timezone.now() - timedelta(minutes=5)
                # Use started_at or created_at since there's no updated_at field
                check_time = existing_collection.started_at or existing_collection.created_at
                if check_time < stale_threshold:
                    logger.info(
                        f"Marking stale in_progress collection {existing_collection.id} as paused "
                        f"(started: {check_time})"
                    )
                    existing_collection.status = 'paused'
                    existing_collection.error_message = 'Collection was interrupted (detected as stale)'
                    existing_collection.save()
                    # Continue to create a new collection
                    existing_collection = None
            
            # For pending collections, also check if stale
            elif existing_collection.status == 'pending':
                from django.utils import timezone
                from datetime import timedelta
                
                stale_threshold = timezone.now() - timedelta(minutes=10)
                if existing_collection.created_at < stale_threshold:
                    logger.info(
                        f"Marking stale pending collection {existing_collection.id} as failed "
                        f"(created: {existing_collection.created_at})"
                    )
                    existing_collection.status = 'failed'
                    existing_collection.error_message = 'Collection was never started'
                    existing_collection.save()
                    existing_collection = None

        if existing_collection:
            logger.info(
                f"Active collection already exists for user {user_id}, "
                f"repository {repository_id} (collection id={existing_collection.id}, "
                f"status={existing_collection.status})"
            )
            return Response({
                'success': True,
                'message': 'Active collection already exists',
                'collection_plan': CollectionSerializer(existing_collection).data,
                'available_metrics': get_metrics_for_platform(platform),
                'platform': platform,
                'is_existing': True
            }, status=status.HTTP_200_OK)

        # Use select_for_update to prevent race conditions
        # Double-check within transaction
        with transaction.atomic():
            from django.utils import timezone
            from datetime import timedelta
            
            existing_check = Collection.objects.select_for_update().filter(
                user=user_id_int,
                repository_id=repository_id,
                status__in=Collection.ACTIVE_STATUSES
            ).first()
            
            if existing_check:
                # Check if it's stale and should be marked as paused/failed
                stale_threshold = timezone.now() - timedelta(minutes=5)
                check_time = existing_check.started_at or existing_check.created_at
                if existing_check.status == 'in_progress' and check_time < stale_threshold:
                    existing_check.status = 'paused'
                    existing_check.error_message = 'Collection was interrupted (detected as stale)'
                    existing_check.save()
                elif existing_check.status == 'pending' and existing_check.created_at < timezone.now() - timedelta(minutes=10):
                    existing_check.status = 'failed'
                    existing_check.error_message = 'Collection was never started'
                    existing_check.save()
                else:
                    return Response({
                        'success': True,
                        'message': 'Active collection already exists',
                        'collection_plan': CollectionSerializer(existing_check).data,
                        'available_metrics': get_metrics_for_platform(platform),
                        'platform': platform,
                        'is_existing': True
                    }, status=status.HTTP_200_OK)

            # Create a new collection
            collection = Collection.objects.create(
                user=user_id_int,
                workspace_id=validated_data['workspace_id'],
                repository_id=repository_id,
                repository_name=validated_data['repository_name'],
                repository_full_name=validated_data['repository_full_name'],
                platform=platform,
                repository_url=validated_data.get('repository_url'),
                default_branch=validated_data.get('default_branch'),
                external_id=validated_data.get('external_id'),  # GitLab project ID
                token_encrypted=validated_data['token'],
                status='pending'
            )

        logger.info(
            f"New collection created for user {user_id}, "
            f"repository {repository_id} (collection id={collection.id})"
        )

        available_metrics = get_metrics_for_platform(platform)

        return Response({
            'success': True,
            'message': 'Collection created. Now select metrics and filters.',
            'collection_plan': CollectionSerializer(collection).data,
            'available_metrics': available_metrics,
            'platform': platform,
            'is_existing': False
        }, status=status.HTTP_201_CREATED)


class GetBranchesView(APIView):
    """Get list of branches for a repository (requires existing collection)"""
    
    def get(self, request, plan_id):
        user_id = request.headers.get('X-User-ID')
        if not user_id:
            return Response(
                {'error': 'User ID required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        collection = get_object_or_404(
            Collection,
            id=plan_id,
            user=int(user_id)
        )
        
        try:
            branch_fetcher = BranchFetcher(
                platform=collection.platform,
                token=collection.token_encrypted,
                repo_full_name=collection.repository_full_name
            )
            
            branches = branch_fetcher.fetch_branches()
            
            return Response({
                'success': True,
                'branches': branches,
                'default_branch': collection.default_branch
            })
            
        except Exception as e:
            logger.error(f"Error fetching branches: {e}")
            return Response({
                'success': False,
                'error': str(e),
                'branches': []
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ConfigureMetricsView(APIView):
    """Configure metrics, filters, and branch for a collection"""
    
    def post(self, request, plan_id):
        user_id = request.headers.get('X-User-ID')
        if not user_id:
            return Response(
                {'error': 'User ID required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        collection = get_object_or_404(
            Collection,
            id=plan_id,
            user=int(user_id)
        )
        
        if collection.status not in ['pending', 'failed', 'paused']:
            return Response(
                {'error': 'Can only configure metrics for pending, failed, or paused collections'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = MetricsFilterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        validated_data = serializer.validated_data
        
        collection.selected_metrics = validated_data['selected_metrics']
        collection.filters = {
            'start_date': validated_data.get('start_date').isoformat() if validated_data.get('start_date') else None,
            'end_date': validated_data.get('end_date').isoformat() if validated_data.get('end_date') else None,
            'status': validated_data.get('status', []),
        }
        
        if 'branch_name' in request.data:
            collection.branch_name = request.data['branch_name']
        
        collection.save()
        
        logger.info(f"Metrics configured for collection {plan_id}: {validated_data['selected_metrics']}")
        
        return Response({
            'success': True,
            'message': 'Metrics and filters configured successfully',
            'collection_plan': CollectionSerializer(collection).data
        })


class ValidateCollectionPlanView(APIView):
    """Show collection summary before starting collection"""
    
    def get(self, request, plan_id):
        user_id = request.headers.get('X-User-ID')
        if not user_id:
            return Response(
                {'error': 'User ID required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        collection = get_object_or_404(
            Collection,
            id=plan_id,
            user=int(user_id)
        )
        
        summary = {
            'collection_plan': CollectionSerializer(collection).data,
            'summary': {
                'repository': collection.repository_full_name,
                'platform': collection.platform,
                'branch': collection.branch_name or collection.default_branch,
                'metrics_count': len(collection.selected_metrics),
                'metrics': collection.selected_metrics,
                'filters': collection.filters,
            }
        }
        
        return Response(summary)


class ExecuteCollectionView(APIView):
    """Start the actual data collection in background"""
    
    def post(self, request, plan_id):
        user_id = request.headers.get('X-User-ID')
        if not user_id:
            return Response(
                {'error': 'User ID required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        collection = get_object_or_404(
            Collection,
            id=plan_id,
            user=int(user_id)
        )
        
        if collection.status not in ['pending', 'failed']:
            return Response(
                {'error': f'Cannot start collection with status: {collection.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not collection.selected_metrics:
            return Response(
                {'error': 'No metrics selected. Configure metrics first.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        run_collection_in_background(plan_id)
        
        return Response({
            'success': True,
            'message': 'Collection started in background',
            'collection_plan': CollectionSerializer(collection).data
        })


class CollectionStatusView(APIView):
    """Get the status of a collection"""
    
    def get(self, request, plan_id):
        user_id = request.headers.get('X-User-ID')
        if not user_id:
            return Response(
                {'error': 'User ID required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        collection = get_object_or_404(
            Collection,
            id=plan_id,
            user=int(user_id)
        )
        
        return Response({
            'collection_plan': CollectionSerializer(collection).data,
            'status': collection.status,
            'progress_percentage': collection.progress_percentage,
            'collected_items': collection.collected_items,
            'total_items': collection.total_items,
            'stats': collection.stats,
            'can_resume': collection.can_resume,
            'last_collected_item': collection.last_collected_item_id
        })


class CollectionPlanListView(APIView):
    """List all collections for a user"""
    
    def get(self, request):
        user_id = request.headers.get('X-User-ID')
        if not user_id:
            return Response(
                {'error': 'User ID required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        collections = Collection.objects.filter(user=int(user_id))
        serializer = CollectionSerializer(collections, many=True)
        
        return Response(serializer.data)


class CollectionHistoryView(APIView):
    """Get collection history for a specific repository"""
    
    def get(self, request, repository_id):
        user_id = request.headers.get('X-User-ID')
        if not user_id:
            return Response(
                {'error': 'User ID required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Include completed, paused, failed, and in_progress collections
        # in_progress is included so users can see orphaned collections (e.g., after container restart)
        # Exclude only pending (which haven't started yet)
        collections = Collection.objects.filter(
            user=int(user_id),
            repository_id=repository_id,
            status__in=['completed', 'paused', 'failed', 'in_progress']
        ).order_by('-created_at')
        
        serializer = CollectionSerializer(collections, many=True)
        
        return Response({
            'success': True,
            'collections': serializer.data,
            'total': collections.count()
        })


class CollectedDataView(APIView):
    """
    Get collected data for a collection from MinIO
    """
    
    def get(self, request, plan_id):
        user_id = request.headers.get('X-User-ID')
        if not user_id:
            return Response(
                {'error': 'User ID required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        collection = get_object_or_404(
            Collection,
            id=plan_id,
            user=int(user_id)
        )
        
        try:
            minio_client = MinIOClient()
            
            # Check if we have a filename stored
            if collection.raw_data_filename:
                # Fetch data from MinIO
                raw_data = minio_client.get_json(collection.raw_data_filename)
                
                if raw_data:
                    return Response({
                        'collection_plan_id': plan_id,
                        'raw_data': raw_data,
                        'stats': collection.stats,
                        'filename': collection.raw_data_filename,
                        'platform': collection.platform
                    })
                else:
                    # File exists in DB but not in MinIO
                    logger.error(f"File {collection.raw_data_filename} not found in MinIO")
                    return Response({
                        'collection_plan_id': plan_id,
                        'raw_data': {},
                        'stats': collection.stats,
                        'message': 'Data file not found in storage',
                        'platform': collection.platform
                    }, status=status.HTTP_404_NOT_FOUND)
            else:
                # No filename yet (collection not started or in progress)
                return Response({
                    'collection_plan_id': plan_id,
                    'raw_data': {},
                    'stats': collection.stats,
                    'message': 'No data collected yet',
                    'platform': collection.platform
                })
                
        except Exception as e:
            logger.error(f"Error retrieving data from MinIO: {e}")
            return Response({
                'error': 'Failed to retrieve collected data',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DataCleaningConfigView(APIView):
    """
    Get current data for cleaning configuration
    """
    
    def get(self, request, plan_id):
        user_id = request.headers.get('X-User-ID')
        if not user_id:
            return Response(
                {'error': 'User ID required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        collection = get_object_or_404(
            Collection,
            id=plan_id,
            user=int(user_id)
        )
        
        if collection.status != 'completed':
            return Response(
                {'error': 'Can only clean completed collections'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get raw data from MinIO
        minio_client = MinIOClient()
        
        if not collection.raw_data_filename:
            return Response(
                {'error': 'No raw data file found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        raw_data = minio_client.get_json(collection.raw_data_filename)
        
        if not raw_data:
            return Response(
                {'error': 'Raw data not found in storage'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Extract metadata for filters
        item_key = 'pull_requests' if collection.platform == 'github' else 'merge_requests'
        items = raw_data.get(item_key, [])
        
        # Get unique authors
        authors = set()
        file_extensions = set()
        
        for item in items:
            # Authors
            author = item.get('details', {}).get('user', {}).get('login') or \
                    item.get('details', {}).get('author', {}).get('username')
            if author:
                authors.add(author)
            
            # File extensions
            files = item.get('files', [])
            for file in files:
                filename = file.get('filename') or file.get('new_path')
                if filename and '.' in filename:
                    ext = filename.split('.')[-1]
                    file_extensions.add(f".{ext}")
        
        return Response({
            'success': True,
            'collection_plan_id': plan_id,
            'platform': collection.platform,
            'total_items': len(items),
            'available_filters': {
                'authors': sorted(list(authors)),
                'file_extensions': sorted(list(file_extensions))
            }
        })


class ApplyFiltersAndCreateCSVView(APIView):
    """
    Apply filters and create structured CSV
    """
    
    def post(self, request, plan_id):
        user_id = request.headers.get('X-User-ID')
        if not user_id:
            return Response(
                {'error': 'User ID required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        collection = get_object_or_404(
            Collection,
            id=plan_id,
            user=int(user_id)
        )
        
        # Get filters from request
        filters = {
            'file_extensions': request.data.get('file_extensions', []),
            'authors': request.data.get('authors', []),
            'keyword_field': request.data.get('keyword_field'),
            'keywords': request.data.get('keywords', []),
            'replace_json': request.data.get('replace_json', False)
        }
        
        try:
            minio_client = MinIOClient()
            
            # Get raw data
            if not collection.raw_data_filename:
                return Response(
                    {'error': 'No raw data file found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            raw_data = minio_client.get_json(collection.raw_data_filename)
            if not raw_data:
                return Response(
                    {'error': 'Raw data not found in storage'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Apply filters and generate CSV
            csv_generator = CSVGenerator(collection.platform)
            filtered_data = csv_generator.apply_filters(raw_data, filters)
            csv_content = csv_generator.generate_csv(filtered_data)
            
            # Generate statistics CSV
            stats_generator = StatisticsCSVGenerator(collection.platform)
            stats_csv_content = stats_generator.generate_statistics_csv(filtered_data, collection)
            
            # Save structured CSV
            structured_filename = minio_client.generate_filename(
                collection.repository_name,
                collection.id,
                'csv'
            )
            minio_client.save_csv(csv_content, structured_filename)
            
            # Save statistics CSV
            stats_filename = f"{collection.repository_name}_stats_{collection.id}.csv"
            minio_client.save_csv(stats_csv_content, stats_filename)
            
            # Update collection
            collection.structured_csv_filename = structured_filename
            collection.statistics_csv_filename = stats_filename
            
            # Delete JSON if requested
            if filters['replace_json']:
                minio_client.delete_file(collection.raw_data_filename)
                collection.raw_data_filename = None
            
            collection.save()
            
            # Get preview data
            preview_data = csv_generator.get_preview(filtered_data, rows=5)
            
            item_key = 'pull_requests' if collection.platform == 'github' else 'merge_requests'
            filtered_count = len(filtered_data.get(item_key, []))
            
            return Response({
                'success': True,
                'message': 'Structured CSV created successfully',
                'csv_filename': structured_filename,
                'statistics_filename': stats_filename,
                'replaced_json': filters['replace_json'],
                'filtered_count': filtered_count,
                'preview': preview_data
            })
            
        except Exception as e:
            logger.error(f"Error creating CSV: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ResumeCollectionView(APIView):
    """
    Resume a paused or failed collection
    """
    
    def post(self, request, plan_id):
        user_id = request.headers.get('X-User-ID')
        if not user_id:
            return Response(
                {'error': 'User ID required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        collection = get_object_or_404(
            Collection,
            id=plan_id,
            user=int(user_id)
        )
        
        if not collection.can_resume:
            return Response(
                {'error': 'Cannot resume this collection'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Start collection in background with resume flag
        run_collection_in_background(plan_id, resume=True)
        
        return Response({
            'success': True,
            'message': 'Collection resumed',
            'last_collected_item': collection.last_collected_item_id
        })


# ============================================================================
# CleanedData Views (formerly in views_cleaning.py)
# ============================================================================

class CollectionCleanedDataListView(APIView):
    """Get all cleaned data for a collection"""
    
    def get(self, request, collection_id):
        user_id = request.headers.get('X-User-ID')
        if not user_id:
            return Response(
                {'error': 'User ID required'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Verify collection belongs to user
        collection = get_object_or_404(
            Collection,
            id=collection_id,
            user=int(user_id)
        )
        
        cleaned_data_list = collection.cleaned_data.all()
        serializer = CleanedDataSerializer(cleaned_data_list, many=True)
        
        return Response({
            'success': True,
            'cleaned_data': serializer.data,
            'collection': {
                'id': collection.id,
                'repository_name': collection.repository_name,
                'status': collection.status,
            }
        })


class CreateCleanedDataView(APIView):
    """Create a new cleaned data instance"""
    
    def post(self, request):
        user_id = request.headers.get('X-User-ID')
        if not user_id:
            return Response(
                {'error': 'User ID required'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        serializer = CreateCleanedDataSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        validated_data = serializer.validated_data
        collection_id = validated_data['collection_id']
        
        # Verify collection belongs to user and is completed
        collection = get_object_or_404(
            Collection,
            id=collection_id,
            user=int(user_id)
        )
        
        if collection.status != 'completed':
            return Response(
                {'error': 'Collection must be completed before cleaning'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create cleaned data instance
        cleaned_data = CleanedData.objects.create(
            collection=collection,
            start_date=validated_data.get('start_date'),
            end_date=validated_data.get('end_date'),
            filters=validated_data.get('filters', {}),
            selected_features=validated_data.get('selected_features', []),
            status='in_progress'
        )
        
        try:
            # Get raw data from MinIO
            minio_client = MinIOClient()
            raw_data = minio_client.get_json(collection.raw_data_filename)
            
            if not raw_data:
                raise Exception("Raw data not found in MinIO")
            
            # Apply date filters if provided
            filtered_data = self._filter_data_by_date(
                raw_data,
                validated_data.get('start_date'),
                validated_data.get('end_date'),
                collection.platform
            )
            
            # Generate CSVs
            csv_generator = CSVGenerator(collection.platform)
            # Apply additional filters from the cleaning request
            if validated_data.get('filters'):
                filtered_data = csv_generator.apply_filters(filtered_data, validated_data['filters'])
            structured_csv = csv_generator.generate_csv(filtered_data)
            
            stats_generator = StatisticsCSVGenerator(collection.platform)
            selected_features = validated_data.get('selected_features', [])
            statistics_csv = stats_generator.generate_statistics_csv(
                filtered_data, 
                collection,
                selected_features=selected_features if selected_features else None
            )
            
            # Generate filenames for CSV files
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            clean_repo_name = collection.repository_name.replace('/', '_').replace(' ', '_').lower()
            structured_filename = f"{clean_repo_name}_cleaneddata{cleaned_data.id}_{timestamp}_structured.csv"
            statistics_filename = f"{clean_repo_name}_cleaneddata{cleaned_data.id}_{timestamp}_statistics.csv"
            
            minio_client.save_csv(structured_csv, structured_filename)
            minio_client.save_csv(statistics_csv, statistics_filename)
            
            # Update cleaned data
            cleaned_data.structured_csv_filename = structured_filename
            cleaned_data.statistics_csv_filename = statistics_filename
            cleaned_data.stats = self._calculate_stats(filtered_data, collection.platform)
            cleaned_data.status = 'completed'
            cleaned_data.save()
            
            logger.info(f"CleanedData {cleaned_data.id} completed successfully")
            
            return Response({
                'success': True,
                'message': 'Cleaning and Filtering Successful',
                'cleaned_data': CleanedDataSerializer(cleaned_data).data
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Error creating cleaned data: {e}")
            cleaned_data.status = 'failed'
            cleaned_data.error_message = str(e)
            cleaned_data.save()
            
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _filter_data_by_date(self, raw_data, start_date, end_date, platform):
        """Filter data by date range"""
        if not start_date and not end_date:
            return raw_data
        
        filtered_data = {}
        item_type = 'pull_requests' if platform == 'github' else 'merge_requests'
        
        if item_type in raw_data:
            filtered_items = []
            for item in raw_data[item_type]:
                created_date = item.get('details', {}).get('created_at', '')
                if created_date:
                    # Parse date and check range
                    item_date = datetime.fromisoformat(created_date.replace('Z', '+00:00')).date()
                    
                    if start_date and item_date < start_date:
                        continue
                    if end_date and item_date > end_date:
                        continue
                    
                    filtered_items.append(item)
            
            filtered_data[item_type] = filtered_items
        
        return filtered_data
    
    def _calculate_stats(self, data, platform):
        """Calculate statistics for cleaned data"""
        stats = {}
        item_type = 'pull_requests' if platform == 'github' else 'merge_requests'
        
        if item_type in data:
            items = data[item_type]
            stats[f'{item_type}_count'] = len(items)
            stats['commits_count'] = sum(len(item.get('commits', [])) for item in items)
            
            if platform == 'github':
                stats['comments_count'] = sum(
                    len(item.get('comments', [])) + len(item.get('reviews', []))
                    for item in items
                )
            else:
                stats['notes_count'] = sum(
                    len(item.get('notes', [])) + len(item.get('discussions', []))
                    for item in items
                )
        
        return stats


class CleanedDataDetailView(APIView):
    """Get details of a specific cleaned data instance"""
    
    def get(self, request, cleaned_data_id):
        user_id = request.headers.get('X-User-ID')
        if not user_id:
            return Response(
                {'error': 'User ID required'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        cleaned_data = get_object_or_404(CleanedData, id=cleaned_data_id)
        
        # Verify collection belongs to user
        if cleaned_data.collection.user != int(user_id):
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = CleanedDataSerializer(cleaned_data)
        return Response(serializer.data)
    
    def delete(self, request, cleaned_data_id):
        """Delete a cleaned data instance"""
        user_id = request.headers.get('X-User-ID')
        if not user_id:
            return Response(
                {'error': 'User ID required'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        cleaned_data = get_object_or_404(CleanedData, id=cleaned_data_id)
        
        # Verify collection belongs to user
        if cleaned_data.collection.user != int(user_id):
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            # Delete files from MinIO
            minio_client = MinIOClient()
            if cleaned_data.structured_csv_filename:
                minio_client.delete_file(cleaned_data.structured_csv_filename)
            if cleaned_data.statistics_csv_filename:
                minio_client.delete_file(cleaned_data.statistics_csv_filename)
            
            cleaned_data.delete()
            
            return Response({
                'success': True,
                'message': 'Cleaned data deleted successfully'
            })
        except Exception as e:
            logger.error(f"Error deleting cleaned data: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@method_decorator(csrf_exempt, name='dispatch')
class DownloadCleanedDataCSVView(View):
    """Download CSV file from a cleaned data instance - uses Django View to bypass DRF"""
    
    def get(self, request, cleaned_data_id, file_type):
        user_id = request.headers.get('X-User-ID')
        if not user_id:
            return HttpResponse(
                '{"error": "User ID required"}',
                status=401,
                content_type='application/json'
            )
        
        try:
            cleaned_data = CleanedData.objects.get(id=cleaned_data_id)
        except CleanedData.DoesNotExist:
            return HttpResponse(
                '{"error": "Cleaned data not found"}',
                status=404,
                content_type='application/json'
            )
        
        # Verify collection belongs to user
        if cleaned_data.collection.user != int(user_id):
            return HttpResponse(
                '{"error": "Permission denied"}',
                status=403,
                content_type='application/json'
            )
        
        if file_type not in ['structured', 'statistics']:
            return HttpResponse(
                '{"error": "Invalid file type"}',
                status=400,
                content_type='application/json'
            )
        
        filename = (cleaned_data.structured_csv_filename 
                   if file_type == 'structured' 
                   else cleaned_data.statistics_csv_filename)
        
        if not filename:
            return HttpResponse(
                '{"error": "File not found"}',
                status=404,
                content_type='application/json'
            )
        
        try:
            minio_client = MinIOClient()
            # Use get_csv_bytes to preserve exact binary content
            csv_bytes = minio_client.get_csv_bytes(filename)
            
            if csv_bytes is None:
                return HttpResponse(
                    '{"error": "File not found in storage"}',
                    status=404,
                    content_type='application/json'
                )
            
            # Use FileResponse with BytesIO for proper file download
            file_like = io.BytesIO(csv_bytes)
            response = FileResponse(
                file_like,
                as_attachment=True,
                filename=filename,
                content_type='text/csv'
            )
            return response
            
        except Exception as e:
            logger.error(f"Error downloading CSV: {e}")
            return HttpResponse(
                '{"error": "File not found in storage"}',
                status=404,
                content_type='application/json'
            )


class DownloadCollectionJSONView(APIView):
    """Download raw JSON data from a collection"""
    
    def get(self, request, collection_id):
        user_id = request.headers.get('X-User-ID')
        if not user_id:
            return Response(
                {'error': 'User ID required'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        collection = get_object_or_404(
            Collection,
            id=collection_id,
            user=int(user_id)
        )
        
        if not collection.raw_data_filename:
            return Response(
                {'error': 'No data file available'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            minio_client = MinIOClient()
            json_data = minio_client.get_json(collection.raw_data_filename)
            
            response = HttpResponse(
                json.dumps(json_data, indent=2),
                content_type='application/json'
            )
            response['Content-Disposition'] = f'attachment; filename="{collection.raw_data_filename}"'
            response['Access-Control-Expose-Headers'] = 'Content-Disposition'
            return response
            
        except Exception as e:
            logger.error(f"Error downloading JSON: {e}")
            return Response(
                {'error': 'File not found in storage'},
                status=status.HTTP_404_NOT_FOUND
            )


class DeleteCollectionView(APIView):
    """Delete a collection and all its related data"""
    
    def delete(self, request, collection_id):
        user_id = request.headers.get('X-User-ID')
        if not user_id:
            return Response(
                {'error': 'User ID required'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        collection = get_object_or_404(
            Collection,
            id=collection_id,
            user=int(user_id)
        )
        
        try:
            minio_client = MinIOClient()
            
            # Delete all cleaning files
            for cleaned_data in collection.cleaned_data.all():
                if cleaned_data.structured_csv_filename:
                    minio_client.delete_file(cleaned_data.structured_csv_filename)
                if cleaned_data.statistics_csv_filename:
                    minio_client.delete_file(cleaned_data.statistics_csv_filename)
            
            # Delete raw data file
            if collection.raw_data_filename:
                minio_client.delete_file(collection.raw_data_filename)
            
            # Delete legacy CSV files if they exist
            if collection.structured_csv_filename:
                minio_client.delete_file(collection.structured_csv_filename)
            if collection.statistics_csv_filename:
                minio_client.delete_file(collection.statistics_csv_filename)
            
            # Delete collection (cascade will delete cleaned data)
            collection.delete()
            
            logger.info(f"Collection {collection_id} deleted successfully")
            
            return Response({
                'success': True,
                'message': 'Collection and all related data deleted successfully'
            })
            
        except Exception as e:
            logger.error(f"Error deleting collection: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class UserDatasetsView(APIView):
    """
    Get all datasets (collections and cleaned data) for a user
    """
    def get(self, request):
        user_id = request.headers.get('X-User-ID')
        
        if not user_id:
            return Response(
                {'error': 'X-User-ID header is required'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        try:
            user_id = int(user_id)
        except (ValueError, TypeError):
            return Response(
                {'error': 'Invalid user_id format'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        logger.info(f"Fetching datasets for user {user_id}")
        
        collections_query = Collection.objects.filter(user=user_id)
        
        collections = collections_query.select_related().prefetch_related('cleaned_data')
        
        # Serialize data
        collections_data = CollectionSerializer(collections, many=True).data
        
        response_data = {
            'user_id': user_id,
            'total_collections': collections.count(),
            'collections': collections_data,
        }
        
        cleaned_data_list = []
        for collection in collections:
            cleaned_items = collection.cleaned_data.all()
            for cleaned in cleaned_items:
                cleaned_data_list.append({
                    **CleanedDataSerializer(cleaned).data,
                    'collection_id': collection.id,
                    'repository_name': collection.repository_name,
                    'repository_full_name': collection.repository_full_name,
                    'platform': collection.platform,
                    'repository_url': collection.repository_url,
                    'repository_id': collection.repository_id,
                    'workspace_id': collection.workspace_id,
                })
        
        response_data['total_cleaned_datasets'] = len(cleaned_data_list)
        response_data['cleaned_datasets'] = cleaned_data_list
        
        # Global statistics
        response_data['statistics'] = {
            'total_items_collected': sum(c.collected_items for c in collections),
            'active_collections': collections.filter(status__in=Collection.ACTIVE_STATUSES).count(),
            'completed_collections': collections.filter(status='completed').count(),
            'failed_collections': collections.filter(status='failed').count(),
        }
        
        logger.info(f"Returning {collections.count()} collections for user {user_id}")
        
        return Response(response_data, status=status.HTTP_200_OK)


# Backward compatibility aliases
CollectionCleaningsListView = CollectionCleanedDataListView
CreateCleaningView = CreateCleanedDataView
CleaningDetailView = CleanedDataDetailView
DownloadCleaningCSVView = DownloadCleanedDataCSVView