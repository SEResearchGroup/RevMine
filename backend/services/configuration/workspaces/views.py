from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
import requests
from .models import Workspace
from .serializers import WorkspaceSerializer, WorkspaceListSerializer, TestConnectionSerializer


class WorkspaceViewSet(viewsets.ModelViewSet):
    # permission_classes = []
    serializer_class = WorkspaceSerializer
    lookup_field = 'id'

    def get_queryset(self):
        if not self.request.user_id:  
            return Workspace.objects.none()
        return Workspace.objects.filter(user=self.request.user_id)

    def get_serializer_class(self):
        if self.action == 'list':
            return WorkspaceListSerializer
        return WorkspaceSerializer

    def perform_create(self, serializer):
        if not self.request.user_id:  
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        # Tout se passe ici → plus propre
        workspace = serializer.save(user=self.request.user_id)
        # Le token est déjà chiffré dans le serializer (via set_token dans save())

    def create(self, request, *args, **kwargs):
        if not request.user_id:  
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # On récupère le token brut avant qu'il soit retiré
        token = serializer.validated_data.pop('token')
        
        workspace = Workspace(user=request.user_id, **serializer.validated_data)
        workspace.set_token(token)
        workspace.save()

        return Response(WorkspaceSerializer(workspace).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        if not request.user_id:  
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        token = serializer.validated_data.pop('token', None)
        workspace = serializer.save()  # met à jour les champs normaux
        
        if token is not None:
            workspace.set_token(token)
            workspace.save()

        return Response(WorkspaceSerializer(workspace).data)

    @action(detail=False, methods=['post'])
    def test_connection(self, request):
        if not request.user_id:  
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        serializer = TestConnectionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        platform = serializer.validated_data['platform']
        token = serializer.validated_data['token']
        url = serializer.validated_data.get('url', '').strip()

        try:
            if platform == 'github':
                resp = requests.get(
                    'https://api.github.com/user',
                    headers={'Authorization': f'token {token}'},
                    timeout=10
                )
            else:
                api_url = url.rstrip('/') + '/api/v4' if url else 'https://gitlab.com/api/v4'
                resp = requests.get(
                    f'{api_url}/user',
                    headers={'PRIVATE-TOKEN': token},
                    timeout=10
                )

            if resp.status_code == 200:
                return Response({
                    'success': True,
                    'message': 'Connexion réussie !',
                    'user': resp.json()
                })
            elif resp.status_code == 401:
                return Response({'success': False, 'message': 'Token invalide'}, status=400)
            else:
                return Response({'success': False, 'message': f'Erreur {resp.status_code}'}, status=400)

        except requests.RequestException as e:
            return Response({'success': False, 'message': str(e)}, status=400)

    @action(detail=True, methods=['post'],url_path='test')
    def test(self, request, pk=None):
        if not request.user_id:  
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        workspace = self.get_object()
        token = workspace.get_token()
        api_url = workspace.get_api_base_url()

        try:
            if workspace.platform == 'github':
                resp = requests.get(f'{api_url}/user', headers={'Authorization': f'token {token}'}, timeout=10)
            else:
                resp = requests.get(f'{api_url}/user', headers={'PRIVATE-TOKEN': token}, timeout=10)

            if resp.status_code == 200:
                return Response({'success': True, 'user': resp.json()})
            else:
                return Response({'success': False, 'message': 'Connexion échouée'}, status=400)
        except Exception as e:
            return Response({'success': False, 'message': str(e)}, status=500)