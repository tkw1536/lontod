"""Utility functions."""

# spellchecker:words ONTDOC RDFS VANN onts trpls trpl ASGS orcid xlink evenodd uriref setclass inferencing elems specialised

from rdflib import Graph


def sort_ontology(ont_orig: Graph) -> Graph:
    """Create a copy of the supplied ontology, sorted by subjects."""
    trpls = ont_orig.triples((None, None, None))
    trpls_srt = sorted(trpls)
    ont_sorted = Graph(
        bind_namespaces="core",
        namespace_manager=ont_orig.namespace_manager,
    )
    for trpl in trpls_srt:
        ont_sorted.add(trpl)
    return ont_sorted


class PylodeError(Exception):
    """An error from PyLode."""
