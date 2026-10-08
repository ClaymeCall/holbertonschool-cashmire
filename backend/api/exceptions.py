import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler


logger = logging.getLogger(__name__)


def sanitized_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        return response

    logger.error(
        "Unhandled API exception",
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    return Response(
        {
            "error": "INTERNAL_SERVER_ERROR",
            "message": "An internal server error occurred.",
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
