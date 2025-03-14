from typing import Tuple, override

from rdflib import URIRef
from rdflib.namespace import NamespaceManager


class BrokenSplitNamespaceManager(NamespaceManager):
    """Implements a NamespaceManager for when .split() is broken because of a trailing '/'"""

    @override
    def compute_qname(self, uri: str, generate: bool = True) -> Tuple[str, URIRef, str]:
        try:
            return super().compute_qname(uri, generate)
        except ValueError:
            if not uri.endswith("/"):
                raise
            return super().compute_qname(uri.rstrip("/"), generate)

    @override
    def compute_qname_strict(
        self, uri: str, generate: bool = True
    ) -> Tuple[str, str, str]:
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
