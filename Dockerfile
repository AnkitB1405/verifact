# Two stages so the runtime image carries no build toolchain.
FROM python:3.13-slim AS build
WORKDIR /app
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
# `python -m venv` seeds an older setuptools than the base image's system copy.
# CVE-2025-47273 (path traversal) is fixed in 78.1.1; upgrade before installing
# anything so the scan has nothing to report.
RUN pip install --no-cache-dir --upgrade "pip" "setuptools>=78.1.1" "wheel"
COPY pyproject.toml README.md ./
COPY src ./src
# Core only. The transformer extra is ~2GB and is installed at run time by
# whoever wants it, so the default image stays small and CI stays fast.
RUN pip install --no-cache-dir ".[postgres]"

# Strip the installer from the venv once installation is finished.
#
# pip bundles vendored copies of urllib3, msgpack, setuptools and others, and
# declares them in pip/_vendor/vendor.txt plus a CycloneDX SBOM. Trivy reads
# that SBOM, so the image reports HIGH findings for versions the application
# never imports - it runs from this venv and the vendored tree is pip's own.
#
# Upgrading our dependencies does not clear them, because they are not our
# dependencies. Removing the installer does, truthfully: a runtime container
# has no reason to be able to install packages, so this is hardening and not a
# way of silencing the scan.
RUN pip uninstall -y pip setuptools wheel 2>/dev/null || true; \
    rm -rf /opt/venv/lib/python3.*/site-packages/pip \
           /opt/venv/lib/python3.*/site-packages/pip-*.dist-info \
           /opt/venv/lib/python3.*/site-packages/setuptools \
           /opt/venv/lib/python3.*/site-packages/setuptools-*.dist-info \
           /opt/venv/lib/python3.*/site-packages/pkg_resources \
           /opt/venv/lib/python3.*/site-packages/wheel \
           /opt/venv/lib/python3.*/site-packages/wheel-*.dist-info \
           /opt/venv/bin/pip*

FROM python:3.13-slim AS runtime
# curl is needed by the healthcheck below and nothing else.
RUN apt-get update && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/* \
 && useradd --create-home --uid 10001 verifact
COPY --from=build /opt/venv /opt/venv

# Same reasoning for the base image's system Python: its pip is never used,
# because every entry point runs from /opt/venv.
RUN rm -rf /usr/local/lib/python3.*/site-packages/pip \
           /usr/local/lib/python3.*/site-packages/pip-*.dist-info \
           /usr/local/lib/python3.*/site-packages/setuptools* \
           /usr/local/lib/python3.*/site-packages/pkg_resources \
           /usr/local/lib/python3.*/ensurepip \
           /usr/local/bin/pip*

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
