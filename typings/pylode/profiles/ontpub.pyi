from _typeshed import Incomplete
from pathlib import Path
from pylode.rdf_elements import AGENT_PROPS as AGENT_PROPS, CLASS_PROPS as CLASS_PROPS, ONTDOC as ONTDOC, ONT_PROPS as ONT_PROPS, PROP_PROPS as PROP_PROPS
from pylode.utils import PylodeError as PylodeError, back_onts_label_props as back_onts_label_props, get_ns as get_ns, load_background_onts as load_background_onts, load_background_onts_titles as load_background_onts_titles, load_ontology as load_ontology, make_pylode_logo as make_pylode_logo, prop_obj_pair_html as prop_obj_pair_html, section_html as section_html, sort_ontology as sort_ontology
from pylode.version import __version__ as __version__
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
    def __init__(self, ontology: Graph | Path | str, sort_subjects: bool = False) -> None: ...
    def make_html(self, destination: Path = None, include_css: bool = True): ...
