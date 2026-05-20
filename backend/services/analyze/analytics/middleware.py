from django.http import JsonResponse


class UserInjectionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user_id = request.headers.get("X-User-ID")

        if not user_id:
            return JsonResponse({"error": "Authentication required"}, status=401)

        try:
            request.user_id = int(user_id)
        except (ValueError, TypeError):
            return JsonResponse({"detail": "Invalid user ID"}, status=401)

        return self.get_response(request)
