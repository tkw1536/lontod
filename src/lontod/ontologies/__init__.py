"""ontology parsing."""

from .ontology import NoOntologyFoundError, Ontology
from .owl import owl_ontology

__all__ = ["NoOntologyFoundError", "Ontology", "owl_ontology"]
