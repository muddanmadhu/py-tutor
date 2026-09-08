FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# docker-cli lets the API launch sibling runner containers via the mounted socket.
RUN apt-get update \
 && apt-get install -y --no-install-recommends docker.io curl \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /srv/app

COPY pyproject.toml ./
COPY app ./app
RUN pip install --no-cache-dir ".[ai]"

COPY alembic.ini ./
COPY alembic ./alembic

RUN groupadd --gid 5001 api && useradd --uid 5001 --gid 5001 --no-create-home api
USER api

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
