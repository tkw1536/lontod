"""http utility functions for daemon."""

from collections.abc import Awaitable, Callable, Iterable
from logging import Logger
from typing import Any, final, override

from mimeparse import MimeTypeParseException, best_match
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


def negotiate(
    req: Request,
    offers: Iterable[str],
    default: str | None = None,
) -> str | None:
    """Negotiates an appropriate content type for a request.

    Args:
        req (Request): Request to negotiate content-type for.
        offers (Iterable[str]): The list of possible content types.
        default (Optional[str], optional): The default content type to return if none of offers matches the request. Defaults to None.

    Returns:
        Optional[str]: A content type from offers, or default if none matches.

    """
    accepts = req.headers.getlist("accept")
    if len(accepts) == 0:
        return default

    try:
        return best_match(offers, ",".join(accepts)) or default
    except MimeTypeParseException:
        return default


@final
class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all requests into the given logger."""

    def __init__(self, *args: Any, logger: Logger, **kwargs: Any) -> None:
        """Create a new middleware."""
        super().__init__(*args, **kwargs)
        self._logger = logger

    @override
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)
        self._logger.debug(
            "%s %s - %d",
            request.method,
            request.url.path,
            response.status_code,
        )
        return response
