# lontod

(Documentation work in progress)

lontod is a daemon that serves OWL ontologies as linked open data.

It consists of two main executables:

- lontod_index (`python -m lontod.cli.index`): Adds or updates an OWL ontology into an sqlite-powered database index. 
- lontod_server (`python -m lontod.cli.server`): Exposes indexed ontologies via http to users

## Development

Dependencies are managed via [poetry](https://python-poetry.org). 

Source code should be formated using `black` and `isort`. 
It should be linted using `pylint` and `mypy`.
These are all installed as development dependencies by poetry.

To run all formatting and linting do:

```bash
black src/
isort src/

pylint src/
mypy src/
```