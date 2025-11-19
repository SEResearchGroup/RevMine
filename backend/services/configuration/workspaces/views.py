from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
import requests
from .models import Workspace
from .serializers import WorkspaceSerializer, WorkspaceListSerializer, TestConnectionSerializer


class WorkspaceConnectionTester:
    """Service pour tester les connexions aux APIs Git"""
    
    @staticmethod
    def test_connection(platform: str, token: str, url: str = None) -> dict:
        """
        Teste la connexion à l'API Git
        Returns: {'success': bool, 'message': str, 'user_data': dict}
        """
        try:
            if platform == 'github':
                api_url = 'https://api.github.com'
                headers = {'Authorization': f'token {token}'}
            elif platform == 'gitlab':
                api_url = 'https://gitlab.com/api/v4'
                headers = {'PRIVATE-TOKEN': token}
            else:  # gitlab_self
                if not url:
                    return {'success': False, 'message': 'URL requise pour GitLab self-hosted'}
                api_url = url.rstrip('/') + '/api/v4'
                headers = {'PRIVATE-TOKEN': token}

            resp = requests.get(
                f'{api_url}/user',
                headers=headers,
                timeout=10
            )

            if resp.status_code == 200:
                return {
                    'success': True,
                    'message': 'Connexion réussie',
                    'user_data': resp.json()
                }
            elif resp.status_code == 401:
                return {'success': False, 'message': 'Token invalide ou expiré'}
            else:
                return {'success': False, 'message': f'Erreur API: {resp.status_code}'}

        except requests.Timeout:
            return {'success': False, 'message': 'Timeout: le serveur ne répond pas'}
        except requests.RequestException as e:
            return {'success': False, 'message': f'Erreur de connexion: {str(e)}'}


class WorkspaceListCreateView(APIView):
    """
    GET /api/workspaces/ - Liste tous les workspaces de l'utilisateur
    POST /api/workspaces/ - Crée un nouveau workspace (avec test de connexion)
    """
    
    def get(self, request):
        """Liste tous les workspaces de l'utilisateur connecté"""
        if not request.user_id:
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        workspaces = Workspace.objects.filter(user=request.user_id)
        serializer = WorkspaceListSerializer(workspaces, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        """Crée un workspace après validation de la connexion"""
        if not request.user_id:
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        serializer = WorkspaceSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)        
        platform = serializer.validated_data['platform']
        token = serializer.validated_data.pop('token')
        url = serializer.validated_data.get('url')
        
        # Test de connexion AVANT de sauvegarder
        connection_result = WorkspaceConnectionTester.test_connection(platform, token, url)
        
        if not connection_result['success']:
            return Response(
                {
                    'error': 'Connection test failed',
                    'message': connection_result['message']
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Si la connexion est OK, on sauvegarde
        workspace = Workspace(user=request.user_id, **serializer.validated_data)
        workspace.set_token(token)
        workspace.save()
        
        return Response(
            {
                'workspace': WorkspaceSerializer(workspace).data,
                'connection_test': connection_result
            },
            status=status.HTTP_201_CREATED
        )


class WorkspaceDetailView(APIView):
    """
    GET /api/workspaces/{id}/ - Détails d'un workspace
    PUT /api/workspaces/{id}/ - Modifie un workspace (avec test si token change)
    PATCH /api/workspaces/{id}/ - Modifie partiellement un workspace
    DELETE /api/workspaces/{id}/ - Supprime un workspace
    """
    
    def get_object(self, request, workspace_id):
        """Récupère le workspace si l'utilisateur en est propriétaire"""
        workspace = get_object_or_404(Workspace, id=workspace_id, user=request.user_id)
        return workspace
    
    def get(self, request, workspace_id):
        """Récupère les détails d'un workspace"""
        if not request.user_id:
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        workspace = self.get_object(request, workspace_id)
        serializer = WorkspaceSerializer(workspace)
        return Response(serializer.data)
    
    def put(self, request, workspace_id):
        """Mise à jour complète d'un workspace"""
        return self._update(request, workspace_id, partial=False)
    
    def patch(self, request, workspace_id):
        """Mise à jour partielle d'un workspace"""
        return self._update(request, workspace_id, partial=True)
    
    def _update(self, request, workspace_id, partial=False):
        """Logique commune pour PUT et PATCH"""
        if not request.user_id:
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        workspace = self.get_object(request, workspace_id)
        serializer = WorkspaceSerializer(workspace, data=request.data, partial=partial)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Si le token est modifié, on teste la connexion
        token = serializer.validated_data.pop('token', None)
        
        if token is not None:
            platform = serializer.validated_data.get('platform', workspace.platform)
            url = serializer.validated_data.get('url', workspace.url)
            
            connection_result = WorkspaceConnectionTester.test_connection(platform, token, url)
            
            if not connection_result['success']:
                return Response(
                    {
                        'error': 'Connection test failed',
                        'message': connection_result['message']
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Sauvegarde des modifications
        workspace = serializer.save()
        
        if token is not None:
            workspace.set_token(token)
            workspace.save()
        
        return Response(WorkspaceSerializer(workspace).data)
    
    def delete(self, request, workspace_id):
        """Supprime un workspace"""
        if not request.user_id:
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        workspace = self.get_object(request, workspace_id)
        workspace.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class WorkspaceTestConnectionView(APIView):
    """
    POST /api/workspaces/test-connection/ - Teste une connexion sans sauvegarder
    POST /api/workspaces/{id}/test/ - Teste la connexion d'un workspace existant
    """
    
    def post(self, request, workspace_id=None):
        """Teste une connexion (existante ou nouvelle)"""
        if not request.user_id:
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Test d'un workspace existant
        if workspace_id:
            workspace = get_object_or_404(Workspace, id=workspace_id, user=request.user_id)
            token = workspace.get_token()
            platform = workspace.platform
            url = workspace.url
        # Test avant création
        else:
            serializer = TestConnectionSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            platform = serializer.validated_data['platform']
            token = serializer.validated_data['token']
            url = serializer.validated_data.get('url')
        
        result = WorkspaceConnectionTester.test_connection(platform, token, url)
        
        if result['success']:
            return Response(result, status=status.HTTP_200_OK)
        else:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)