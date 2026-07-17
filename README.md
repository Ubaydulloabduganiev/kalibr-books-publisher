# Kalibr Publisher

Kalibr Publisher is Kalibr Books' private internal platform for organizing, scheduling, and publishing **manually prepared** content to Telegram. It does not generate captions, images, or content and has no AI API dependency.

This archive is version **0.1.1**, a repaired deployment-ready foundation for the current two-service Render setup and the planned Ubuntu VPS deployment.

## What works now

- FastAPI API with structured logging, request tracing, stable error envelopes, security headers, liveness/readiness checks, and a useful root endpoint.
- Next.js administration UI in Uzbek and Russian, responsive navigation, dark mode, backend status, direct Telegram text publishing, media uploads, and basic scheduling.
- Supported media: JPEG, PNG, WebP, GIF, MP4, MOV, WebM, PDF, DOC, and DOCX.
- Telegram text, photo, video, animation, document, and mixed photo/video album delivery.
- Persistent local media storage and an atomic JSON post store for the current single-process phase.
- A single-process scheduler that resumes pending JSON-backed schedules after restart.
- A protected browser gateway: temporary Basic Auth at Next.js and a separate shared secret between Next.js and FastAPI.
- Docker development and production builds, Caddy HTTPS configuration, Render Blueprint, and GitHub Actions CI.

## Important current limitation

The post store is an **atomic JSON file**, not the final SQLAlchemy/Alembic database. Therefore:

- Run exactly **one API worker**.
- Do not horizontally scale the API service.
- Treat this version as a corrected operational foundation, not the completed company-wide platform.
- Database-backed idempotency, durable retry history, JWT sessions, audit logs, approvals, and the full media library remain later phases.

## Local Docker start

```bash
cp .env.example .env
# Change ADMIN_BASIC_PASSWORD and INTERNAL_API_KEY.
docker compose up --build
```

Open:

- Web: `http://localhost:3000`
- API root: `http://localhost:8000/`
- API documentation: `http://localhost:8000/docs`
- API readiness: `http://localhost:8000/api/v1/health/ready`

## Quality checks

```bash
make bootstrap
make check
npm run web:build
```

## Deployment

- Render: see [`docs/deployment.md`](docs/deployment.md#render-blueprint-deployment).
- Ubuntu VPS: see [`docs/deployment.md`](docs/deployment.md#ubuntu-vps-deployment).
- Environment variables: [`docs/environment-variables.md`](docs/environment-variables.md).
- API endpoints: [`docs/api.md`](docs/api.md).
- Repair report: [`docs/code-review-phase-1.md`](docs/code-review-phase-1.md).

## Repository layout

```text
apps/api/                 FastAPI API and tests
apps/web/                 Next.js UI and tests
infrastructure/caddy/     HTTPS reverse proxy for VPS deployment
docs/                     Architecture and operating documentation
render.yaml               Render Blueprint
storage/                  Runtime data in a non-container deployment
backups/                  Backup location
logs/                     Optional file logs
tmp/                      Controlled temporary workspace
```

## Ownership

Copyright © 2026 Kalibr Books. Private proprietary software. Unauthorized copying, distribution, or use is prohibited.
