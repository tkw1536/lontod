from logging import Logger
from typing import Awaitable, Callable, Iterable, Optional

from mimeparse import MimeTypeParseException, best_match
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


def negotiate(
    req: Request, offers: Iterable[str], default: Optional[str] = None
) -> Optional[str]:
    """Performs content negotiation to determine the best content type for a request"""

    accepts = req.headers.getlist("accept")
    if len(accepts) == 0:
        return default

    try:
        return best_match(offers, ",".join(accepts))
    except MimeTypeParseException:
        return default


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all requests into the given logger"""

    def __init__(self, *args, logger: Logger, **kwargs):
        super().__init__(*args, **kwargs)
        self._logger = logger

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ):
        response = await call_next(request)
        self._logger.debug(
            f"{request.method} {request.url.path} - {response.status_code} "
        )
        return response
