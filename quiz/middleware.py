# from django.utils.deprecation import MiddlewareMixin
# from django.http import JsonResponse

# class Force200Middleware(MiddlewareMixin):
#     def __init__(self, get_response):
#         self.get_response = get_response

#     def __call__(self, request):
#         # Skip admin, static, media
#         if request.path.startswith('/admin') or request.path.startswith('/static') or request.path.startswith('/media'):
#             return self.get_response(request)

#         # Get bearer token
#         auth_header = request.headers.get("Authorization")
#         bearer_token = None
#         if auth_header and auth_header.startswith("Bearer "):
#             bearer_token = auth_header.split("Bearer ")[1].strip()

#         # Guest token
#         guest_token = (
#             request.session.get("guest_id") or
#             request.headers.get("Guest-Token") or
#             request.META.get("HTTP_GUEST_TOKEN") or
#             bearer_token
#         )

#         # Restricted paths
#         restricted_paths = [
#             '/api/private/',
#             '/quiz/leader_board/',
#         ]
#         if not guest_token and not request.user.is_authenticated:
#             for path in restricted_paths:
#                 if request.path.startswith(path):
#                     return JsonResponse({
#                         "type": "error",
#                         "message": "Authentication or guest token required",
#                         "data": {}
#                     }, status=200)

#         try:
#             # Normal processing
#             response = self.get_response(request)

#             if response.status_code != 200:
#                 message = getattr(response, 'reason_phrase', 'An error occurred')
#                 data = {}

#                 if hasattr(response, 'data'):
#                     if isinstance(response.data, dict):
#                         message = response.data.get('detail') or str(response.data)
#                         data = response.data
#                     else:
#                         message = str(response.data)

#                 return JsonResponse({
#                     "type": "error",
#                     "message": message,
#                     "data": data if isinstance(data, dict) else {}
#                 }, status=200)

#             return response

#         except Exception as e:
#             return JsonResponse({
#                 "type": "error",
#                 "message": str(e),
#                 "data": {}
#             }, status=200)


from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
import json

class Force200Middleware(MiddlewareMixin):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith('/admin') or request.path.startswith('/static') or request.path.startswith('/media'):
            return self.get_response(request)

        try:
            response = self.get_response(request)

            # If response status is 200, return as is
            if response.status_code == 200:
                return response

            # Try to access response content
            content_type = response.get('Content-Type', '')
            if 'application/json' in content_type:
                try:
                    data = json.loads(response.content.decode())
                except Exception:
                    data = {}

                message = (
                    data.get('detail') or
                    data.get('message') or
                    'Validation Error' if response.status_code == 400 else
                    response.reason_phrase or 'An error occurred'
                )

                return JsonResponse({
                    "type": "error",
                    "message": message,
                    "data": data if isinstance(data, dict) else {}
                }, status=200)

            # Fallback for non-JSON responses
            return JsonResponse({
                "type": "error",
                "message": response.reason_phrase or 'An error occurred',
                "data": {}
            }, status=200)

        except Exception as e:
            return JsonResponse({
                "type": "error",
                "message": str(e),
                "data": {}
            }, status=200)

