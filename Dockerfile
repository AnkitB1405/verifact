# Two stages so the runtime image carries no build toolchain.
FROM python:3.13-slim AS build
WORKDIR /app
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY pyproject.toml README.md ./
COPY src ./src
# Core only. The transformer extra is ~2GB and is installed at run time by
# whoever wants it, so the default image stays small and CI stays fast.
RUN pip install --no-cache-dir ".[postgres]"

FROM python:3.13-slim AS runtime
# curl is needed by the healthcheck below and nothing else.
RUN apt-get update && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/* \
 && useradd --create-home --uid 10001 verifact
COPY --from=build /opt/venv /opt/venv
WORKDIR /app
COPY --chown=verifact:verifact alembic.ini ./
COPY --chown=verifact:verifact alembic ./alembic
COPY --chown=verifact:verifact config ./config
USER verifact
ENV PATH="/opt/venv/bin:$PATH" PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS http://localhost:8000/api/v1/health || exit 1
CMD ["uvicorn", "verifact.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
