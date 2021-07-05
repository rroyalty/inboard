ARG PYTHON_VERSION=3.9
FROM python:${PYTHON_VERSION} AS base
LABEL org.opencontainers.image.authors="Brendon Smith <bws@bws.bio>"
LABEL org.opencontainers.image.description="Docker images and utilities to power your Python APIs and help you ship faster."
LABEL org.opencontainers.image.licenses="MIT"
LABEL org.opencontainers.image.source="https://github.com/br3ndonland/inboard"
LABEL org.opencontainers.image.title="inboard"
LABEL org.opencontainers.image.url="https://github.com/users/br3ndonland/packages/container/package/inboard"
ENV APP_MODULE=inboard.app.main_base:app PATH=/opt/poetry/bin:$PATH POETRY_HOME=/opt/poetry POETRY_VIRTUALENVS_CREATE=false PYTHONPATH=/app
COPY poetry.lock pyproject.toml /app/
WORKDIR /app/
RUN curl -fsS -o install-poetry.py https://raw.githubusercontent.com/python-poetry/poetry/HEAD/install-poetry.py && \
  python install-poetry.py -y && poetry install --no-dev --no-interaction --no-root
COPY inboard /app/inboard
ENTRYPOINT ["python"]
CMD ["-m", "inboard.start"]

FROM base AS fastapi
ENV APP_MODULE=inboard.app.main_fastapi:app
RUN poetry install --no-dev --no-interaction --no-root -E fastapi

FROM base AS starlette
ENV APP_MODULE=inboard.app.main_starlette:app
RUN poetry install --no-dev --no-interaction --no-root -E starlette
