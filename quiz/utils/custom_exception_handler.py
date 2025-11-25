from rest_framework.views import exception_handler
from rest_framework.response import Response

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        message = response.data.get("detail", "An error occurred")
        return Response({
            "type": "error",
            "message": message,
            "data": {}
        }, status=200)

    # Fallback for unhandled exceptions
    return Response({
        "type": "error",
        "message": str(exc),
        "data": {}
    }, status=200)
