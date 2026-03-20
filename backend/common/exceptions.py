import logging
import uuid

from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    request = context.get("request")
    request_id = getattr(request, "request_id", str(uuid.uuid4()))

    if response is not None:
        response.data["request_id"] = request_id
    else:
        logger.error(
            "Unhandled exception [request_id=%s]: %s",
            request_id,
            str(exc),
            exc_info=True,
            extra={"request_id": request_id},
        )

    return response
