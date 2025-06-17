# lontod
lontod is a daemon that serves OWL ontologies as linked open data.

It consists of two main executables:

- lontod_server (`python -m lontod.cli.server`): Exposes ontologies via http to users. 
- lontod_index (`python -m lontod.cli.index`): Adds or updates an OWL ontology into an sqlite-powered database index. 

These are described in detail the 'Server' and 'Indexing' sections below.

## Server

The server provides a set of ontologies to users. 
It implements three routes:

- an overview page, providing a list of all ontologies (by default under the root url `/`)
- one page for each ontology (by default also under the root url at `/?identifier=${ontology_identifier}`)
- redirects from the URI of defined concepts to the appropriate documentation page (everywhere else)

The ontology pages perform [Content Negotiation](https://en.wikipedia.org/wiki/Content_negotiation) using the standard HTTP `Accept` header by default.
Each ontology can be returned using different formats, some human-readable and some machine-readable (see the Indexing Internals section below for a list of supported formats).
Alternatively, a specific content type can be specified using a `format` URL parameter.

The Base URL for the overview page and ontology pages can be configured using a command line flag or the `LONTOD_ROUTE` environment variable.
It defaults to `/`. 
When not the root URL, the root URL with redirect to the base URL. 

The server can be started using:

```bash

# index the 'ontologies' direcory in-memory and start exposing any contained ontologies
lontod_server ontologies/

# start the server - listens on localhost:8080 by default
# by default this serves a previously indexed ontology - see indexing below.
lontod_server

# start the server in 'watch mode': Automatically index the directory whenever anything changes.
# This maintains an index in memory by default.
lontod_server --watch "ontologies/"

# load an index from the file 'my_index.db' and listen on host 0.0.0.0 and port 3000
lontod_server --host 0.0.0.0 --port 3000 --database my_index.db
```

The server additionally supports the following environment variables:

| Name                       | Default     | Description                                                    |
|----------------------------|-------------|----------------------------------------------------------------|
| `LONTOD_HOST`              | (none)      | The hostname to listen on                                      |
| `LONTOD_PORT`              | (none)      | The port to listen on                                          |
| `LONTOD_DB`                | (in-memory) | Database filename                                              |
| `LONTOD_PATHS`             | (none)      | The set of paths to index, separated by `;`                    |
| `LONTOD_ROUTE`             | `/`         | The URL route to server ontologies from, must start with a `/` |
| `LONTOD_LANGUAGES`         | (none)      | (Spoken) languages to present defienanda for, separated by `;` |
| `LONTOD_INDEX_HTML_HEADER` | (none)      | Path to a html file to prefix index html responses with        |
| `LONTOD_INDEX_HTML_FOOTER` | (none)      | Path to a html file to suffix index html responses with        |
| `LONTOD_INDEX_TXT_HEADER`  | (none)      | Path to a text file to prefix index txt responses with         |
| `LONTOD_INDEX_TXT_FOOTER`  | (none)      | Path to a text file to suffix index txt responses with         |

## Indexing

To enable the server, ontologies have to first be indexed. 
The index is stored in an sqlite database called `lontod.index` in the current directory by default. 

This can be achieved using the `lontod_index` program:

```bash
# index a single file
lontod_index my_ontology.owl

# index multiple files
lontod_index my_ontology.owl second_ontology.owl

# index a directory (not recursive)
lontod_index ontologies/
```

The indexer supports the following environment variables:


| Name                       | Default          | Description                                                    |
|----------------------------|------------------|----------------------------------------------------------------|
| `LONTOD_DB`                | `./lontod.index` | Database filename                                              |
| `LONTOD_PATHS`             | (none)           | The set of paths to index, separated by `;`                    |
| `LONTOD_LANGUAGES`         | (none)           | (Spoken) languages to present defienanda for, separated by `;` |
| `LONTOD_INDEX_HTML_HEADER` | (none)           | Path to a html file to prefix index html responses with        |
| `LONTOD_INDEX_HTML_FOOTER` | (none)           | Path to a html file to suffix index html responses with        |
| `LONTOD_INDEX_TXT_HEADER`  | (none)           | Path to a text file to prefix index txt responses with         |
| `LONTOD_INDEX_TXT_FOOTER`  | (none)           | Path to a text file to suffix index txt responses with         |

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

### Indexing internals

This section briefly describes the internals of the indexing process.

The index consists of an SQLITE database with the following schema (omitting indexes):

```sql

-- indexed concepts and ontologies
CREATE TABLE IF NOT EXISTS "DEFINIENDA" (
    "URI"           TEXT NOT NULL, -- uri of the indexed concept (or ontology)
    "ONTOLOGY_ID"   TEXT NOT NULL, -- internal identifier of the ontology (usually filename, used in some server URIs)
    "CANONICAL"     INTEGER NOT NULL, -- is the URI a canonical URI or derived (e.g. via a versionIRI)
    "FRAGMENT"      TEXT -- html fragment identifier (without #) that the definition is found in, or NULL in case of ONTOLOGY
);

-- encoding of ontologies in various different formats
-- each indexed ontology will be stored in the formats listed below.
CREATE TABLE IF NOT EXISTS "DATA" (
    "ONTOLOGY_ID"   TEXT NOT NULL,
    "MIME_TYPE"     TEXT NOT NULL,
    "DATA"          BLOB NOT NULL
);

-- a view to list all existing ontologies
CREATE VIEW IF NOT EXISTS
    "ONTOLOGIES"
AS SELECT
  NAMES.ONTOLOGY_ID, -- the id of the ontology
  NAMES.URI, -- the primary URI of the ontology 
  (
    SELECT
        JSON_GROUP_ARRAY(DEFINIENDA.URI)
    FROM
        DEFINIENDA
    WHERE
        DEFINIENDA.ONTOLOGY_ID = NAMES.ONTOLOGY_ID
        AND DEFINIENDA.CANONICAL IS FALSE
        AND DEFINIENDA.FRAGMENT IS NULL
    ORDER BY DEFINIENDA.URI
  ) AS ALTERNATE_URIS, -- list of alternate URIS
  (
    SELECT
        COUNT(*)
    FROM
        DEFINIENDA
    WHERE
        DEFINIENDA.CANONICAL IS TRUE
        AND DEFINIENDA.ONTOLOGY_ID = NAMES.ONTOLOGY_ID
  ) AS DEFINIENDA_COUNT,
  (
    SELECT
        JSON_GROUP_ARRAY(DATA.MIME_TYPE)
        FROM
            DATA
        WHERE
            DATA.ONTOLOGY_ID = NAMES.ONTOLOGY_ID
        ORDER BY
            DATA.MIME_TYPE
  ) AS MIME_TYPES -- the mime types the ontology is available as
FROM 
  DEFINIENDA AS NAMES 
WHERE
    NAMES.FRAGMENT IS NULL
    AND NAMES.CANONICAL IS TRUE
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

# Deployment

The included [Dockerfile](./Dockerfile) contains a docker file with all required libraries. 
It is also deployed as a [GitHub Package](https://github.com/tkw1536/lontod/pkgs/container/lontod) 

It starts `lontod_server` and indexes the directory `/data/` by default.
It also supports the environment variables read by the server with the following defaults:
- `LONTOD_HOST`: `0.0.0.0` (listen on all interfaces)
- `LONTOD_PATHS`: `/data/`
- `LONTOD_LANGUAGES`: `en`

To run the docker image you can use something like:

```bash
# to index once and serve it
docker run -ti -p 8080:8080 -v /path/to/ontologies/:/data/:ro ghcr.io/tkw1536/lontod:latest

# to index and watch the directory
docker run -ti -p 8080:8080 -v /path/to/ontologies/:/data/:ro ghcr.io/tkw1536/lontod:latest --watch
```

## LICENSE

None, the code is provided only so that you may inspect it.
