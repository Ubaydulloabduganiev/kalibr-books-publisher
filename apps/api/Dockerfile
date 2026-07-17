# syntax=docker/dockerfile:1.7

FROM python:3.12.11-slim-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

COPY --from=ghcr.io/astral-sh/uv:0.11.28 /uv /uvx /bin/

RUN groupadd --gid 10001 kalibr \
    && useradd --uid 10001 --gid kalibr --create-home --shell /usr/sbin/nologin kalibr

WORKDIR /app

COPY apps/api/pyproject.toml apps/api/uv.lock apps/api/README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY apps/api/src ./src
RUN uv sync --frozen --no-dev

FROM base AS development

RUN uv sync --frozen --all-groups
USER kalibr
EXPOSE 8000
CMD ["uvicorn", "kalibr_publisher.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--no-access-log"]

FROM base AS production

# Run as root so the app can create /data/* runtime dirs on Render's mounted disk.
# Render forwards external traffic to its $PORT (10000). Listen on 10000 explicitly.
EXPOSE 10000
# Diagnostic wrapper: surface startup state to stdout (visible in Render dashboard logs)
CMD ["sh", "-c", "echo '=== BOOT DIAG ==='; echo \"PYTHON=$(python --version 2>&1)\"; echo \"UVICORN=$(which uvicorn)\"; echo \"PWD=$(pwd)\"; echo '--- import test ---'; python -c \"import kalibr_publisher.main as m; print('IMPORT_OK app=', hasattr(m,'app'))\" 2>&1; echo '--- starting uvicorn ---'; exec uvicorn kalibr_publisher.main:app --host 0.0.0.0 --port 10000 --workers 1 --log-level debug --no-access-log --proxy-headers --forwarded-allow-ips '*'"]
