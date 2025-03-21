# lontod

(Documentation work in progress)

lontod is a daemon that serves OWL ontologies as linked open data.

It consists of two main executables:

- lontod_server (`python -m lontod.cli.server`): Exposes indexed ontologies via http to users
- lontod_index (`python -m lontod.cli.index`): Adds or updates an OWL ontology into an sqlite-powered database index. 

## Server

The server provides a set of ontologies to users. 
It implements three routes:

- an overview page, providing a list of all ontologies (under the root url `/`)
- one page for each ontology (under `/ontology/${ontology_name}`)
- redirects from the URI of defined concepts to the appropriate documentation page (everywhere else)

The ontology pages perform [Content Negotiation](https://en.wikipedia.org/wiki/Content_negotiation) using the standard HTTP `Accept` header. 
Each ontology can be returned using different formats, some human-readable and some machine-readable (see the Indexing Internals section below for a list of supported formats).


## Indexing

To enable the server, ontologies have to first be indexed. 
This can be achieved using the `lontod_index` program:

```bash
# index a single file
lontod_index my_ontology.owl

# index multiple files
lontod_index my_ontology.owl second_ontology.owl

# index a directory (not recursive)
lontod_index ontologies/
```

Ontologies are indexed using the filename as a name. 
For example `my_ontology.owl` will be indexed under the name `my_ontology`.
If the indexer encounters an existing indexed ontology with the same name, it is overwritten. 
If the indexer encountered a different indexed ontology with the same base URI, it is overwritten and the old slug is removed. 

The indexer uses [rdflib](https://rdflib.readthedocs.io/en/stable/index.html) for parsing and converting ontologies.
When indexing, the format is selected based on the file extension:

| Format                                                                       | File Extension                 |
|------------------------------------------------------------------------------|--------------------------------|
| [RDF/XML](https://www.w3.org/TR/REC-rdf-syntax/)                             | `.rdf`, `.xml`, `.owl`         |
| [N3](https://www.w3.org/TeamSubmission/n3/)                                  | `.n3`                          |
| [Turtle](https://www.w3.org/TR/turtle/)                                      | `.ttl`, `.turtle`              |
| [N-Triples](https://www.w3.org/TR/n-triples/)                                | `.nt`                          |
| [TriG](https://www.w3.org/TR/trig/)                                          | `.trig`                        |
| [Trix](https://web.archive.org/web/20110724134923/http://sw.nokia.com/trix/) | `.trix`                        |
| [RDFa](https://www.w3.org/TR/rdfa-primer/)                                   | `.xhtml`, `.html`, `.svg`      |
| [JSON-LD](https://json-ld.org/)                                              | `.json`, `.jsonld`, `.json-ld` |
| [HexTuples](https://github.com/ontola/hextuples)                             | `.hext`                        |
| [N-Quads](https://www.w3.org/TR/n-quads/)                                    | `.nq`, `.nquads`               |


## Indexing internals

This section briefly describes the internals of the indexing process.

The index consists of an SQLITE databse with the following schema (omitting indexes):

```sql
-- names of indexed ontologies for use in server URLs
CREATE TABLE IF NOT EXISTS "NAMES" (
    "SLUG"    TEXT NOT NULL PRIMARY KEY, -- "name" of the ontology
    "URI"   TEXT NOT NULL
) STRICT;

-- encoding of ontology in various different formats
-- each indexed ontology will be stored in the formats listed below.
CREATE TABLE IF NOT EXISTS "ONTOLOGIES" (
    "URI"        TEXT NOT NULL,
    "MIME_TYPE" TEXT NOT NULL,
    "DATA"      BLOB NOT NULL
) STRICT;

-- defienda found in ontologies
CREATE TABLE IF NOT EXISTS "DEFINIENDA" (
    "URI"       TEXT NOT NULL, -- URI of defiendum
    "ONTOLOGY"  TEXT NOT NULL, -- ontology it is defined in
    "FRAGMENT"  TEXT -- html fragment identifier (without #) that the definition is found in
) STRICT;
```

Each indexed ontology is first loaded and then converted into each of the following formats:

| Format                                           | Media-Type             |
|--------------------------------------------------|------------------------|
| [RDF/XML](https://www.w3.org/TR/REC-rdf-syntax/) | `application/rdf+xml`  |
| [N3](https://www.w3.org/TeamSubmission/n3/)      | `text/n3`              |
| [Turtle](https://www.w3.org/TR/turtle/)          | `text/turtle`          |
| [N-Triples](https://www.w3.org/TR/n-triples/)    | `text/plain`           |
| [TriG](https://www.w3.org/TR/trig/)              | `application/trig`     |
| [JSON-LD](https://json-ld.org/)                  | `application/ld+json`  |
| [HexTuples](https://github.com/ontola/hextuples) | `application/x-ndjson` |
| HTML                                             | `text/html`            |

The HTML representation is created using [pyLODE](https://github.com/rdflib/pyLODE/).
All other representations are created using rdflib.
They are all stored in the `ONTOLOGIES` table.

To allow for defienda-resolving, the generated html is additionally scanned for fragments in which each definiendum is shown.
This makes use of [Beautiful Soup](https://www.crummy.com/software/BeautifulSoup/). 
These are stored in the `DEFINIENDA` table.

## Development

Dependencies are managed via [poetry](https://python-poetry.org). 
We use [Poe the Poet](https://poethepoet.natn.io) as a task runner. 

Source code be linted using `pylint` and `mypy`.
It should be formated using `black` and `isort`. 
Tests are run using `pytest`. 

To run all of these, the following tasks are defined.
Assuming development dependencies are installed, simply run:

- `poe format` to format code in-place.
- `poe lint`: to run all linters
- `poe test`: to run all the tests

See `pyproject.toml` for details on which task runs which exact underlying commands. 