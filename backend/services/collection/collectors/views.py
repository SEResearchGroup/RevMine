from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import StartCollectionSerializer, CollectionPlanSerializer
from .models import CollectionPlan
import logging

logger = logging.getLogger(__name__)


class StartCollectionView(APIView):
    """
    Start a data collection for a repository
    """
    
    def post(self, request):
        """
        Receive repository details and create a collection plan
        """
        # Get user_id from header (sent by API Gateway)
        user_id = request.headers.get('X-User-ID')
        if not user_id:
            return Response(
                {'error': 'User ID required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Validate incoming data
        serializer = StartCollectionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        validated_data = serializer.validated_data
        
        # ========== PRINT PROJECT DETAILS ==========
        print("\n" + "="*80)
        print(" COLLECTION SERVICE - PROJECT DETAILS RECEIVED")
        print("="*80)
        print(f" User ID: {user_id}")
        print(f" Repository ID: {validated_data['repository_id']}")
        print(f" Workspace ID: {validated_data['workspace_id']}")
        print(f" Repository Name: {validated_data['repository_name']}")
        print(f" Full Name: {validated_data['repository_full_name']}")
        print(f" Platform: {validated_data['platform']}")
        if 'repository_url' in validated_data:
            print(f" URL: {validated_data['repository_url']}")
        if 'default_branch' in validated_data:
            print(f" Default Branch: {validated_data['default_branch']}")
        print("="*80 + "\n")
        
        # Log the details
        logger.info(f"Collection started for repository: {validated_data['repository_full_name']}")
        
        # Create a collection plan
        collection_plan = CollectionPlan.objects.create(
            user=int(user_id),
            workspace_id=validated_data['workspace_id'],
            repository_id=validated_data['repository_id'],
            repository_name=validated_data['repository_name'],
            repository_full_name=validated_data['repository_full_name'],
            platform=validated_data['platform'],
            status='pending'
        )
        
        return Response({
            'success': True,
            'message': 'Collection plan created successfully',
            'collection_plan': CollectionPlanSerializer(collection_plan).data
        }, status=status.HTTP_201_CREATED)


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