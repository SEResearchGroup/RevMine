


class UserInjectionMiddleware:
    """
    Middleware to inject user_id from X-User-ID header
    sent by API Gateway
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        user_id = request.headers.get('X-User-ID')
        
        if user_id:
            try:
                request.user_id = int(user_id)
            except (ValueError, TypeError):
                request.user_id = None
        else:
            request.user_id = None
        
        return self.get_response(request)
    
