FROM python:3.13-bullseye as builder

RUN pip install poetry==2.1.1

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

WORKDIR /app

COPY pyproject.toml poetry.lock ./
RUN touch README.md

RUN --mount=type=cache,target=$POETRY_CACHE_DIR poetry install --without dev --no-root

FROM python:3.13-slim-bullseye as runtime

ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH"
COPY --from=builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}

COPY src/lontod ./lontod

EXPOSE 8080

ENV LONTOD_HOST=0.0.0.0\
    LONTOD_PORT=8080

ENV LONTOD_LANGUAGES=en,de
ENTRYPOINT ["python", "-m", "lontod.cli.server"]
CMD ["--watch", "/data/"]