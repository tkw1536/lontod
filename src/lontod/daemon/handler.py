"""http http handler."""

from collections import OrderedDict
from collections.abc import Callable, Generator
from functools import wraps
from logging import Logger
from traceback import format_exception
from typing import Any, Final, final
from urllib.parse import quote

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse
from starlette.routing import BaseRoute, Route

from lontod.html import (
    BR,
    CODE,
    FIELDSET,
    LEGEND,
    LI,
    SPAN,
    UL,
    A,
    RawNode,
    stream_nodes,
)
from lontod.index import Query
from lontod.ontologies.types import extension_from_type
from lontod.utils.pool import Pool

from .http import LoggingMiddleware, negotiate

# spellchecker:words noopener noreferer tabindex

DEFAULT_INDEX_HTML_HEADER: Final[str] = """
<!DOCTYPE html>
<html lang="en">
<head>
<style>
    main { margin: 1em }
    span { display: block; margin-bottom: 1em; }
    ul { margin-top: 0; margin-bottom: 0; }
    ul:not(:last-child) { margin-bottom: 1em; }
    main a, main a:visited{ color:blue; }
    footer { font-size:small; color: gray; }
    footer a, footer a:visited { color: black; }
    fieldset { margin-bottom: 1em; }
</style>
<title>Ontologies</title>
</head>
<h1>Ontologies</h1>
<main>
"""

DEFAULT_INDEX_TXT_HEADER: Final[str] = """# Ontologies:
"""

DEFAULT_INDEX_HTML_FOOTER: Final[str] = """
</main>
<footer>
    Powered by <a href='https://github.com/tkw1536/lontod' target='_blank' rel='noopener noreferer'>lontod</a>
</footer>
"""

DEFAULT_INDEX_TXT_FOOTER: Final[str] = """
---
Powered by lontod: https://github.com/tkw1536/lontod
"""


@final
class Handler(Starlette):
    """Handler class for the ontology serving daemon."""

    __public_domain: str | None
    __ontology_route: str
    __insecure_skip_routes: bool
    __index_txt_header: str
    __index_txt_footer: str
    __pool: Pool[Query]
    __logger: Logger

    def __init__(  # noqa: PLR0913
        self,
        pool: Pool[Query],
        logger: Logger,
        ontology_route: str = "/",
        public_domain: str | None = None,
        insecure_skip_routes: bool = False,
        index_html_header: str | None = None,
        index_html_footer: str | None = None,
        index_txt_header: str | None = None,
        index_txt_footer: str | None = None,
        debug: bool = False,
    ) -> None:
        """Create a new handler."""
        self.__public_domain = public_domain
        self.__ontology_route = ontology_route
        self.debug = debug
        self.__pool = pool
        self.__logger = logger
        self.__insecure_skip_routes = insecure_skip_routes

        self.__index_html_header = RawNode(
            index_html_header or DEFAULT_INDEX_HTML_HEADER
        )
        self.__index_html_footer = RawNode(
            index_html_footer or DEFAULT_INDEX_HTML_FOOTER
        )
        self.__index_txt_header = index_txt_header or DEFAULT_INDEX_TXT_HEADER
        self.__index_txt_footer = index_txt_footer or DEFAULT_INDEX_TXT_FOOTER

        super().__init__(
            routes=list(self.__routes),
            middleware=[
                Middleware(LoggingMiddleware, logger=logger),
            ],
            debug=debug,
        )

    @property
    def __routes(self) -> Generator[BaseRoute]:
        yield Route(self.__ontology_route, self.handle)

        if not self.__insecure_skip_routes:
            # for safety
            yield Route("/.well-known/{path:path}", Response("Not Found", 404))

            # for speed - don't bother with these
            yield Route("/favicon.ico", Response("Not Found", 404))
            yield Route("/robots.txt", Response("Not Found", 404))

        yield Route("/{path:path}", self.handle_fallback)

    def reverse_url(
        self,
        identifier: str | None = None,
        typ: str | None = None,
        fragment: str | None = None,
        download: bool = False,
    ) -> str:
        """Return the (server-local) url to retrieve a specific ontology."""
        params: OrderedDict[str, str | None] = OrderedDict()
        params["identifier"] = identifier
        params["format"] = typ
        params["download"] = "1" if download else None

        path = self.__ontology_route

        query = "&".join(
            [
                f"{key}={quote(value)}"
                for (key, value) in params.items()
                if isinstance(value, str)
            ],
        )
        if query != "":
            query = "?" + query

        frag = "#" + fragment if isinstance(fragment, str) else ""

        return path + query + frag

    @property
    def logger(self) -> Logger:
        """Logger associated with this handler."""
        return self.__logger

    @staticmethod
    def _catch_handler_error(
        func: Callable[..., Response],
    ) -> Callable[..., Response]:
        """Wrap a handler to safely catch all errors."""

        @wraps(func)
        def wrapper(
            self: "Handler",
            req: Request,
            *args: Any,
            **kwargs: Any,
        ) -> Response:
            try:
                return func(self, req, *args, **kwargs)
            except Exception as err:
                self.logger.exception("handler failed", exc_info=err)
                text = (
                    "".join(format_exception(err))
                    if self.debug
                    else "Internal Server Error"
                )
                return self.error_response(500, text)

        return wrapper

    @_catch_handler_error
    def handle_fallback(self, req: Request) -> Response:
        """Handle a fallback request to lookup a definition."""
        # find the hostname to use for URI lookup!
        prefix = (
            self.__public_domain
            if isinstance(self.__public_domain, str)
            else req.url.hostname
        )
        if prefix is None:
            return self.error_response(404, "not found")

        # find the exact IRI requested
        iri_noproto = "://" + prefix + req.url.path.rstrip("/")

        self.__logger.debug("looking up IRIs %r", iri_noproto)

        candidates = (
            f"http{iri_noproto}",
            f"https{iri_noproto}",
            f"http{iri_noproto}/",
            f"https{iri_noproto}/",
        )

        with self.__pool.use() as query:
            defs = query.get_definienda(*candidates)

            try:
                first_def = next(defs)
            except StopIteration:
                return self.__serve_final_fallback(req)

            # pick the last URL, ordered by slug!
            url = self.reverse_url(
                first_def.ontology_identifier,
                None,
                fragment=first_def.fragment,
            )
            return self.redirect_response(url, status_code=303)

    def __serve_final_fallback(self, req: Request) -> Response:
        if req.url.path != "/":
            return self.error_response(404, "not found")

        return self.redirect_response(
            self.reverse_url(identifier=None, typ=None, fragment=None, download=False),
            status_code=303,
        )

    def redirect_response(self, dest: str, status_code: int = 307) -> Response:
        """Create a generic response that redirects the user to the given destination."""
        return Response(
            content=f"Redirecting to {dest}...",
            status_code=status_code,
            headers={
                "location": quote(dest, safe=":/%#?=@[]!$&'()*+,;"),
            },
        )

    def error_response(self, code: int, message: str) -> Response:
        """Create a generic error response with the given message and code."""
        return Response(
            status_code=code,
            media_type="text/plain",
            content=message,
        )

    @_catch_handler_error
    def handle(self, req: Request) -> Response:
        """Handle a request to the main route."""
        typ = req.query_params.get("format")
        identifier = req.query_params.get("identifier")
        download = req.query_params.get("download") == "1"

        if not isinstance(identifier, str):
            return self.handle_root(req, typ)

        return self.handle_ontology(req, identifier, typ, download)

    def handle_root(self, req: Request, typ: str | None = None) -> Response:
        """Handle the "/" url."""
        self.__logger.debug("handle_root(typ=%r)", typ)

        if not isinstance(typ, str):
            typ = negotiate(req, ("text/plain", "text/html"), default="text/plain")
            if typ is None:
                msg = "negotiate returned None"
                raise AssertionError(msg)

        return self.serve_index(typ)

    def handle_ontology(
        self,
        req: Request,
        identifier: str,
        typ: str | None,
        download: bool,
    ) -> Response:
        """Handle the get ontology rendering route."""
        self.__logger.debug(
            "handle_ontology(identifier=%r, typ=%r,download=%r)",
            identifier,
            typ,
            download,
        )

        with self.__pool.use() as query:
            if not isinstance(typ, str):
                # find the mime times we can serve for this ontology
                offers = list(query.get_mime_types(identifier))
                if len(offers) == 0:
                    return self.error_response(404, "Ontology not found")

                # decide on the actual content type
                decision = negotiate(req, offers)
                if decision is None or decision not in offers:
                    decision = "text/plain" if "text/plain" in offers else None

                if decision is None:
                    return self.error_response(406, "No available content type")
            else:
                if not query.has_mime_type(identifier, typ):
                    return self.error_response(404, "Ontology not found")
                decision = typ

            return self.serve_ontology(query, identifier, decision, download)

    def serve_ontology(
        self,
        query: Query,
        identifier: str,
        typ: str,
        download: bool,
    ) -> Response:
        """Serve an ontology with the given identifier and format."""
        self.__logger.debug(
            "serve_ontology(identifier=%r, typ=%r,download=%r)",
            identifier,
            typ,
            download,
        )

        content = query.get_data(identifier, typ)
        # This shouldn't happen.
        # but there is a race condition: if the db changes between the decision
        # and this query, it might disappear.
        if content is None:
            return self.error_response(500, "Negotiated content type went away")

        ext = extension_from_type(typ)
        filename = f"{identifier}.{ext}" if isinstance(ext, str) else identifier

        disposition = (
            f"{'attachment' if download else 'inline'}; filename*=UTF-8''{filename}"
        )
        return Response(
            status_code=200,
            media_type=typ,
            headers={"Content-Disposition": disposition},
            content=content,
        )

    def serve_index(self, typ: str) -> Response:
        """Serve the index document."""
        self.__logger.debug("serve_index(%r)", typ)

        if typ not in {"text/plain", "text/html"}:
            return self.error_response(404, "Not Found")

        if typ != "text/html":
            return StreamingResponse(self.__stream_root_text(), media_type="text/plain")
        return StreamingResponse(self.__stream_root_html(), media_type="text/html")

    def __stream_root_html(self) -> Generator[str]:
        with self.__pool.use() as query:
            return stream_nodes(
                self.__index_html_header,
                (
                    FIELDSET(
                        LEGEND(onto.uri),
                        SPAN(
                            A(
                                "View In Default Format",
                                href=self.reverse_url(onto.identifier),
                            ),
                            BR(),
                            f"{onto.definienda_count} Definienda",
                        ),
                        (
                            "Alternate URIs:",
                            SPAN(
                                UL(LI(CODE(uri)) for uri in onto.alternate_uris),
                            ),
                        )
                        if len(onto.alternate_uris) > 0
                        else None,
                        "Download in other formats:",
                        SPAN(
                            UL(
                                LI(
                                    A(
                                        typ,
                                        href=self.reverse_url(
                                            onto.identifier, typ, download=True
                                        ),
                                    )
                                )
                                for typ in onto.mime_types
                            ),
                        ),
                    )
                    for onto in query.list_ontologies()
                ),
                self.__index_html_footer,
            )

    def __stream_root_text(self) -> Generator[str]:
        with self.__pool.use() as query:
            yield self.__index_txt_header

            for onto in query.list_ontologies():
                yield f"## Ontology {onto.uri}:\n"

                yield f"[{self.reverse_url(onto.identifier, None, download=False)}]\n"
                yield f"{onto.definienda_count} Definienda\n"
                yield "\n"

                yield "Available URIs:\n"
                for uri in onto.alternate_uris:
                    yield f"* {uri}\n"
                yield "\n"

                yield "Available Formats:\n"
                for typ in onto.mime_types:
                    yield f"* {typ} [{self.reverse_url(onto.identifier, typ, download=True)}]\n"
                yield "\n"

                yield self.__index_txt_footer
