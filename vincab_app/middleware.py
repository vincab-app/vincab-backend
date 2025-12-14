import logging
from datetime import datetime

logger = logging.getLogger("backend")

class RequestLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        user = getattr(request, "user", None)
        user_info = user.username if user and user.is_authenticated else "anonymous"

        logger.info(
            f"{request.method} {request.path} | "
            f"User: {user_info} | "
            f"Status: {response.status_code}"
        )

        return response
