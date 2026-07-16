# Kalibr Publisher

Kalibr Publisher is Kalibr Books' private internal platform for organizing, scheduling, and publishing manually created content to Telegram. The application does not generate content and has no dependency on AI or paid APIs.

This repository currently contains **Phase 1: production-grade project foundations**.

## Included in Phase 1

- FastAPI service with typed settings, structured logging, request tracing, consistent API errors, security headers, liveness checks, and real filesystem readiness checks.
- Next.js App Router interface with Uzbek and Russian localization, responsive navigation, dark mode, and live backend status.
- Docker development and production builds.
- Caddy reverse proxy with automatic HTTPS for `publisher.uboom.uz`.
- Persistent host-mounted directories for storage, backups, temporary files, and logs.
- Python and TypeScript linting, strict type checking, automated tests, and GitHub Actions CI.
- Architecture, installation, API, environment, folder-structure, deployment, verification, and Phase 1 decision documentation.

## Requirements

- Docker Engine 26+ with Docker Compose v2, or
- Python 3.12, uv 0.11.28+, Node.js 22, and npm 10 for local non-Docker development.

## Start with Docker

```bash
cp .env.example .env
docker compose up --build
```

Open:

- Web: `http://localhost:3000`
- API documentation: `http://localhost:8000/docs`
- API readiness: `http://localhost:8000/api/v1/health/ready`

## Run quality checks

```bash
make bootstrap
make check
```

## Production

Start with the [`installation guide`](docs/installation.md), then use the [`deployment guide`](docs/deployment.md) for production. Phase 1 endpoints are documented in [`docs/api.md`](docs/api.md), and verification results are recorded in [`docs/verification.md`](docs/verification.md). The intended public address is `https://publisher.uboom.uz`.

## Project layout

```text
apps/api/                 FastAPI application
apps/web/                 Next.js application
infrastructure/caddy/     HTTPS reverse-proxy configuration
docs/                     Architecture and operating documentation
storage/                  Persistent uploaded content at runtime
backups/                  Persistent backup archives at runtime
tmp/                      Controlled temporary workspace
logs/                     Application logs when file output is enabled
```

## Development phases

1. Project architecture — implemented in this archive.
2. Database and migrations.
3. Authentication and session management.
4. Media library.
5. Content management.
6. Durable scheduler.
7. Telegram publishing.
8. Dashboard and calendar.
9. Full test expansion and hardening.
10. Production deployment and operations.

## Ownership

Copyright © 2026 Kalibr Books. Private proprietary software. Unauthorized copying, distribution, or use is prohibited.
