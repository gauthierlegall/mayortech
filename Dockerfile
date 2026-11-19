# Multi-stage pattern from etalab-ia/OpenGateLLM and suitenumerique/docs (MIT).
# Source commits, copied instructions and adaptations: docs/REUTILISATION_CODE.md.
FROM ghcr.io/astral-sh/uv:0.11.27@sha256:4d01caf3b22dfd11003455e2e68153da08c4ee1fa54fdbd166c6282d22693419 AS uv
FROM python:3.11.15-slim-bookworm@sha256:d29f48a31a8b408ed19272ca1e7b10ebae13b240a27e862d3d4217c528e2e0c3 AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
FROM base AS builder
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
ENV UV_PYTHON_DOWNLOADS=0
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY src ./src
COPY web ./web
COPY native-editor/dist ./native-editor/dist
# The target host uses Docker's legacy builder; avoid BuildKit-only cache mounts.
RUN uv sync --frozen --no-cache --no-dev --extra documents --extra exchange --extra calendars --no-editable
FROM base AS runtime
COPY --from=builder /opt/venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH TRAVAUX_DB=/data/travaux.sqlite3
WORKDIR /app
COPY --chown=10001:10001 fixtures/storylines/lovable-v1 ./fixtures/storylines/lovable-v1
RUN useradd --uid 10001 --create-home travaux && mkdir /data && chown travaux:travaux /data
USER 10001:10001
EXPOSE 8765
CMD ["python", "-m", "travaux", "serve", "--host", "0.0.0.0", "--port", "8765"]
