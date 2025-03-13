from rdflib import Graph, Literal


def only_object_lang(g: Graph, lang: str) -> Graph:
    """Restricts a graph to objects of a specific language.

    Args:
        g (Graph): Graph to copy
        lang (str): Language to limit object to

    Returns:
        Graph: A copy of g with triples that are of a language other than lang removed.
    """
    clone = Graph()
    clone.parse(data=g.serialize(format="turtle"), format="turtle")

    for s, p, o in g:
        if not isinstance(o, Literal):
            continue
        if o.language is None or o.language == lang:
            continue
        clone.remove((s, p, o))

    return clone
