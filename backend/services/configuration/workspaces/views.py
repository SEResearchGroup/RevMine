from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Workspace
from .serializers import (
    WorkspaceSerializer, 
    WorkspaceListSerializer,
    TestConnectionSerializer
)

class WorkspaceViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Workspace.objects.filter(user_id=self.request.user.id)
    
    def get_serializer_class(self):
        if self.action == 'list':
            return WorkspaceListSerializer
        return WorkspaceSerializer
    
    @action(detail=False, methods=['post'])
    def test_connection(self, request):
        """Test a new connection before creating a workspace"""
        serializer = TestConnectionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        result = serializer.validate_token_connection()
        
        if result['status'] == 'success':
            return Response({
                'message': 'Connection successful',
                'user_info': result['user']
            })
        else:
            return Response({
                'message': result['message']
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def test(self, request, pk=None):
        """Test an existing workspace"""
        workspace = self.get_object()
        
        try:
            token = workspace.get_token()
            api_url = workspace.get_api_url()
            
            if workspace.platform == 'github':
                response = requests.get(
                    f'{api_url}/user',
                    headers={'Authorization': f'token {token}'},
                    timeout=10
                )
            else:
                response = requests.get(
                    f'{api_url}/user',
                    headers={'PRIVATE-TOKEN': token},
                    timeout=10
                )
            
            if response.status_code == 200:
                return Response({
                    'status': 'success',
                    'message': 'Connection successful',
                    'user': response.json()
                })
            else:
                return Response({
                    'status': 'error',
                    'message': 'Connection failed'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)