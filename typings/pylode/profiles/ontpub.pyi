# pylint: skip-file
from pathlib import Path
from typing import overload

from _typeshed import Incomplete
from rdflib import Graph

RDF_FOLDER: Incomplete

class OntPub:
    ont: Incomplete
    back_onts: Incomplete
    back_onts_titles: Incomplete
    props_labeled: Incomplete
    toc: dict[str, str]
    fids: dict[str, str]
    ns: Incomplete
    doc: Incomplete
    content: Incomplete
    def __init__(
        self, ontology: Graph | Path | str, sort_subjects: bool = False
    ) -> None: ...
    @overload
    def make_html(self, destination: None = None, include_css: bool = True) -> str: ...
    @overload
    def make_html(self, destination: Path, include_css: bool = True) -> None: ...
