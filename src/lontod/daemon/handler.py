"""http http handler"""

from functools import wraps
from html import escape
from logging import Logger
from traceback import format_exception
from typing import Any, Callable, Final, Iterable, Optional, final
from urllib.parse import quote

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse
from starlette.routing import Route

from ..index import Query
from ..utils.pool import Pool
from .http import LoggingMiddleware, negotiate

# spellchecker:words noopener noreferer

DEFAULT_INDEX_HTML_HEADER: Final[
    str
] = """
<!DOCTYPE html>
<style>
    ul a, ul a:visited{ color:blue; }
    footer{ font-size:small; color: gray; }
    footer a, footer a:visited { color: black; }
</style>
<h1>Ontologies</h1>
"""

DEFAULT_INDEX_TXT_HEADER: Final[
    str
] = """Ontologies:
"""

DEFAULT_INDEX_HTML_FOOTER: Final[
    str
] = """
<footer>
    Powered by <a href='https://github.com/tkw1536/lontod' target='_blank' rel='noopener noreferer'>lontod</a>
</footer>
"""

DEFAULT_INDEX_TXT_FOOTER: Final[
    str
] = """
---
Powered by lontod: https://github.com/tkw1536/lontod
"""


@final
class Handler(Starlette):
    """Handler class for the ontology serving daemon"""

    __public_url: str | None
    __index_txt_header: str
    __index_txt_footer: str
    __index_html_header: str
    __index_html_footer: str
    __pool: Pool[Query]
    __logger: Logger

    def __init__(
        self,
        pool: Pool[Query],
        logger: Logger,
        public_url: Optional[str] = None,
        index_html_header: Optional[str] = None,
        index_html_footer: Optional[str] = None,
        index_txt_header: Optional[str] = None,
        index_txt_footer: Optional[str] = None,
        debug: bool = False,
    ):
        super().__init__(
            routes=[
                Route("/", self.handle_root),
                Route("/.well-known/lontod/get", self.handle_ontology),
                # for security!
                Route("/.well-known/{path:path}", Response("Not Found", 404)),
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

        self.__public_url = public_url
        self.debug = debug
        self.__pool = pool
        self.__logger = logger

        self.__index_html_header = index_html_header or DEFAULT_INDEX_HTML_HEADER
        self.__index_html_footer = index_html_footer or DEFAULT_INDEX_HTML_FOOTER
        self.__index_txt_header = index_txt_header or DEFAULT_INDEX_TXT_HEADER
        self.__index_txt_footer = index_txt_footer or DEFAULT_INDEX_TXT_FOOTER

    @property
    def logger(self) -> Logger:
        """logger associated with this handler"""
        return self.__logger

    @staticmethod
    def _catch_handler_error(
        func: Callable[..., Response],
    ) -> Callable[..., Response]:
        """Wraps a handler to safely catch all errors"""

        @wraps(func)
        def wrapper(
            self: "Handler", req: Request, *args: Any, **kwargs: Any
        ) -> Response:
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
            self.__public_url
            if isinstance(self.__public_url, str)
            else req.url.hostname
        )
        if prefix is None:
            return self.error_response(404, "not found")

        # find the exact IRI requested
        iri_noproto = "://" + prefix + req.url.path.rstrip("/")

        self.__logger.debug(f"looking up IRIs {iri_noproto!r}")

        candidates = (
            f"http{iri_noproto}",
            f"https{iri_noproto}",
            f"http{iri_noproto}/",
            f"https{iri_noproto}/",
        )

        with self.__pool.use() as query:
            defs = query.get_definiendum(*candidates)
            if defs is None:
                return self.error_response(404, "not found")

            (slug, uri, fragment) = defs
            url = self._public_url(slug, uri, None, fragment=fragment)
            return self.redirect_response(url, status_code=303)

    @_catch_handler_error
    def redirect_response(self, dest: str, status_code: int = 307) -> Response:
        """Creates a generic response that redirects the user to the given destination"""

        return Response(
            content=f"Redirecting to {dest}...",
            status_code=status_code,
            headers={
                "location": quote(dest, safe=":/%#?=@[]!$&'()*+,;"),
            },
        )

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

    def _stream_root(self, html: bool) -> Iterable[str]:
        if html:
            yield self.__index_html_header
            yield "<ul>"
        else:
            yield self.__index_txt_header

        with self.__pool.use() as query:
            for slug, uri in query.list_ontologies():
                link = self._public_url(slug, uri, None)
                if html:
                    yield f'<li><a href="{escape(link, True)}">{escape(uri)}</a></li>\n'
                else:
                    yield f"* {link}: <{uri}>\n"

        if html:
            yield "</ul>"
            yield self.__index_html_footer
        else:
            yield self.__index_txt_footer

    @_catch_handler_error
    def handle_ontology(self, req: Request) -> Response:
        """Handles the '/_/get?uri=...&format=...' route"""

        uri = req.query_params.get("uri")
        if not isinstance(uri, str):
            return self.error_response(400, "Missing URI")

        typ = req.query_params.get("type")

        with self.__pool.use() as query:
            if not isinstance(typ, str):
                # find the mime times we can serve for this ontology
                offers = query.get_mime_types(uri)
                if len(offers) == 0:
                    return self.error_response(404, "Ontology not found")

                # decide on the actual content type
                decision = negotiate(req, offers)
                if decision is None or decision not in offers:
                    decision = "text/plain" if "text/plain" in offers else None

                if decision is None:
                    return self.error_response(406, "No available content type")
            else:
                if not query.has_mime_type(uri, typ):
                    return self.error_response(404, "Ontology not found")
                decision = typ

            self.__logger.debug("ontology %r: decided on %s", uri, typ)
            return self.serve_ontology(query, uri, decision)

    def serve_ontology(self, query: Query, uri: str, typ: str) -> Response:
        """Serves an ontology with the given URI and format"""
        result = query.get_data(uri, typ)

        # This shouldn't happen.
        # but there is a race condition: if the db changes between the decision
        # and this query, it might disappear.
        if result is None:
            return self.error_response(500, "Negotiated content type went away")

        return Response(status_code=200, media_type=typ, content=result)

    def _public_url(
        self, slug: str, uri: str, typ: str | None = None, fragment: str | None = None
    ) -> str:
        """returns the (server-local) url to retrieve a specific ontology"""
        _ = slug  # unused

        url = f"/.well-known/lontod/get?uri={quote(uri)}"
        if isinstance(typ, str):
            url += "&type=" + quote(typ)
        if isinstance(fragment, str):
            url += "#" + fragment
        return url
