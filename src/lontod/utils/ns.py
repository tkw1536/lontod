"""implements a custom namespace manager."""

from typing import final, override

from rdflib import Graph, URIRef
from rdflib.namespace import NamespaceManager


@final
class BrokenSplitNamespaceManager(NamespaceManager):
    """Implements a NamespaceManager for when .split() is broken because of a trailing '/'."""

    @override
    def __init__(self, graph: Graph) -> None:
        super().__init__(graph, graph._bind_namespaces)  # noqa: SLF001

    @override
    def compute_qname(self, uri: str, generate: bool = True) -> tuple[str, URIRef, str]:
        try:
            return super().compute_qname(uri, generate)
        except ValueError:
            if not uri.endswith("/"):
                raise
            return super().compute_qname(uri.rstrip("/"), generate)

    @override
    def compute_qname_strict(
        self,
        uri: str,
        generate: bool = True,
    ) -> tuple[str, str, str]:
        try:
            return super().compute_qname_strict(uri, generate)
        except ValueError:
            if not uri.endswith("/"):
                raise
            return super().compute_qname_strict(uri.rstrip("/"), generate)

    @override
    def normalizeUri(self, rdfTerm: str) -> str:
        try:
            return super().normalizeUri(rdfTerm)
        except ValueError:
            if not rdfTerm.endswith("/"):
                raise
            return super().normalizeUri(rdfTerm.rstrip("/"))
