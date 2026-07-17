# Current implementation record

Version 0.1.1 contains the repaired project foundation plus a limited manual Telegram publishing and scheduling flow.

## Implemented

- FastAPI and Next.js container foundations.
- Uzbek and Russian UI.
- Render and Ubuntu VPS deployment configuration.
- Temporary Basic Auth and internal gateway key.
- Telegram immediate text publishing.
- Media upload and Telegram media dispatch.
- Atomic JSON post persistence.
- Single-process schedule polling that survives ordinary restarts when storage is persistent.
- Health, logging, validation, security headers, tests, and CI.

## Not yet implemented

- SQLAlchemy models and Alembic migrations.
- JWT login, refresh sessions, CSRF lifecycle, and multi-device session management.
- Full media library records, immutable versions, checksums, previews, archive, and reference protection.
- Durable transactional scheduler claims, retry attempts, grace periods, and idempotency evidence.
- Workflow roles, approval, audit log, notifications, calendar drag-and-drop, dashboard statistics, and backup/restore.

## Run

```bash
cp .env.example .env
make dev
```

## Validate

```bash
make bootstrap
make check
npm run web:build
```
