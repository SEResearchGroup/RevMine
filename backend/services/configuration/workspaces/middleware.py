from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken

class JWTUserIDMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            try:
                access_token = AccessToken(token)
                request.user_id = access_token['user_id']
            except (TokenError, InvalidToken, KeyError):
                print("Invalid token or user_id not found")
                request.user_id = None
        else:
            request.user_id = None
            
        return self.get_response(request)