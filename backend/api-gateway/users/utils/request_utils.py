"""
Utilitaires pour la manipulation des requêtes HTTP
Responsabilité : Extraction et préparation des données de requête
"""
import json
import logging
from django.http import JsonResponse

logger = logging.getLogger(__name__)


def parse_json_body(request):
    """
    Parse le body JSON d'une requête.
    
    Args:
        request: Requête Django
    
    Returns:
        tuple: (data_dict, error_response)
               - Si succès: (data, None)
               - Si erreur: (None, JsonResponse)
    """
    try:
        return json.loads(request.body), None
    except json.JSONDecodeError:
        return None, JsonResponse({'error': 'Invalid JSON'}, status=400)


def prepare_multipart_data(request):
    """
    Prépare les données multipart/form-data.
    
    Args:
        request: Requête Django
    
    Returns:
        tuple: (data_list, files_dict)
    """
    # Préparation des champs de formulaire
    data = []
    for key in request.POST.keys():
        values = request.POST.getlist(key)
        for value in values:
            data.append((key, value))
    
    # Préparation des fichiers
    files = {}
    for key, file in request.FILES.items():
        files[key] = (file.name, file.read(), file.content_type)
    
    return data, files


def prepare_request_data(request):
    """
    Prépare les données de la requête selon le Content-Type.
    
    Args:
        request: Requête Django
    
    Returns:
        tuple: (body, data, files, content_type)
               - body: Corps brut pour JSON
               - data: Liste de tuples pour multipart
               - files: Dict de fichiers pour multipart
               - content_type: Type de contenu à transmettre
    """
    content_type = request.content_type or ''
    
    # Requêtes sans body
    if request.method not in ['POST', 'PUT', 'PATCH']:
        return None, None, None, None
    
    # JSON
    if content_type.startswith('application/json'):
        return request.body, None, None, 'application/json'
    
    # Multipart/form-data
    if content_type.startswith('multipart/form-data'):
        data, files = prepare_multipart_data(request)
        return None, data, files, None
    
    # Autres types
    return request.body, None, None, content_type