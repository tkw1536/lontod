"""ontology parsing"""

from .ontology import NoOntologyFound, Ontology
from .owl import owl_ontology

__all__ = ["Ontology", "NoOntologyFound", "owl_ontology"]
