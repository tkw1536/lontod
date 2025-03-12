from functools import wraps
from html import escape
from logging import Logger
from traceback import format_exception
from typing import Callable, Iterable, Optional
from urllib.parse import quote

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response, StreamingResponse
from starlette.routing import Route

from ..utils.pool import Pool
from ..indexer import Query
from .http import LoggingMiddleware, negotiate


class Handler(Starlette):
    """Handler class for the ontology serving daemon"""

    def __init__(
        self,
        pool: Pool[Query],
        logger: Logger,
        public_url: Optional[str] = None,
        debug: bool = False,
    ):
        super().__init__(
            routes=[
                Route("/", self.handle_root),
                Route("/ontology/{slug}", self.handle_ontology),
                Route("/ontology/{slug}/", self.remove_trailing_slash),
                # for security!
                Route("/.well-known/{path:path}", Response("Forbidden", 403)),
                # for speed - don't bother with these
                Route("/favicon.ico", Response("Not Found", 404)),
                Route("/robots.txt", Response("Not Found", 404)),
                # do the actual lookup
                Route("/{path:path}", self.handle_fallback),
            ],
            middleware=[
                Middleware(LoggingMiddleware, logger=logger),
            ],
            debug=debug,
        )

        self.public_url = public_url
        self.debug = debug
        self.pool = pool
        self.logger = logger

    @staticmethod
    def _catch_handler_error(
        func: Callable[..., Response],
    ) -> Callable[..., Response]:
        """Wraps a handler to safely catch all errors"""

        @wraps(func)
        def wrapper(self: "Handler", req: Request, *args, **kwargs) -> Response:
            try:
                return func(self, req, *args, **kwargs)
            except Exception as err:
                self.logger.error(err)
                text = (
                    "".join(format_exception(err))
                    if self.debug
                    else "Internal Server Error"
                )
                return self.error_response(500, text)

        return wrapper

    @_catch_handler_error
    def handle_fallback(self, req: Request) -> Response:
        """Handles a fallback request to lookup a definition"""

        # find the hostname to use for URI lookup!
        prefix = (
            self.public_url if isinstance(self.public_url, str) else req.url.hostname
        )
        if prefix is None:
            return self.error_response(404, "not found")

        # find the exact IRI requested
        iri_noproto = "://" + prefix + req.url.path.rstrip("/")

        self.logger.debug(f"looking up IRIs {iri_noproto!r}")

        candidates = (
            f"http{iri_noproto}",
            f"https{iri_noproto}",
            f"http{iri_noproto}/",
            f"https{iri_noproto}/",
        )

        with self.pool.use() as query:
            defs = query.get_definiendum(*candidates)
            if defs is None:
                return self.error_response(404, "not found")

            (slug, fragment) = defs
            url = "/ontology/" + slug
            if isinstance(fragment, str):
                url += "#" + quote(fragment)
            return self.redirect_response(url, status_code=303)

    @_catch_handler_error
    def redirect_response(self, dest: str, status_code: int = 307) -> RedirectResponse:
        """Creates a generic response that redirects the user to the given destination"""
        return RedirectResponse(dest, status_code)

    def error_response(self, code: int, message: str) -> Response:
        """Creates a generic error response with the given message and code"""

        return Response(
            status_code=code,
            media_type="text/plain",
            content=message,
        )

    def remove_trailing_slash(self, req: Request) -> Response:
        """Redirects to the same url without a trailing slash.
        If the URL doesn't change as a result, returns 500"""

        path = req.url.path
        clean = path.rstrip("/")

        if path == clean:
            return self.error_response(
                500, "remove_trailing_slash on url without slash"
            )

        return self.redirect_response(clean)

    @_catch_handler_error
    def handle_root(self, req: Request) -> Response:
        """Handles the "/" url"""

        media_type = negotiate(req, ("text/html", "text/plain"), default="text/plain")
        return StreamingResponse(
            self._stream_root(media_type == "text/html"), media_type=media_type
        )

    __root_html_head = """
    <!DOCTYPE html>
    <ul>
    """

    __root_html_foot = """
    </ul>
    """

    def _stream_root(self, html: bool) -> Iterable[str]:
        if html:
            yield Handler.__root_html_head

        with self.pool.use() as query:
            for slug, uri in query.list_ontologies():
                link = "/ontology/" + slug + "/"
                if html:
                    yield f'<li><a href="{escape(link, True)}">{escape(uri)}</a></li>\n'
                else:
                    yield f"* {link}: <{uri}>\n"

        if html:
            yield Handler.__root_html_foot

    @_catch_handler_error
    def handle_ontology(self, req: Request) -> Response:
        """Handles the '/ontology/:slug/' route"""

        slug = req.path_params.get("slug")
        if not isinstance(slug, str):
            raise AssertionError("expected slug parameter to be a string")

        with self.pool.use() as query:

            # find the mime times we can serve for this ontology
            offers = query.get_mime_types(slug)
            if len(offers) == 0:
                return self.error_response(404, "Ontology not found")

            # decide on the actual content type
            decision = negotiate(req, offers)
            if decision is None or decision not in offers:
                decision = "text/plain" if "text/plain" in offers else None

            if decision is None:
                return self.error_response(406, "No available content type")

            self.logger.debug("ontology %r: decided on %s", slug, decision)
            result = query.get_data(slug, decision)
            if result is None:
                return self.error_response(500, "Negotiated content type went away")

            return Response(status_code=200, media_type=decision, content=result)
