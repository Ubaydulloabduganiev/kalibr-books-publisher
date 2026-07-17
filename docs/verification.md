# Verification report — 0.1.1 repair

Verification date: 2026-07-17

## API

- Ruff lint: passed.
- Ruff formatting check: passed.
- mypy strict mode on application source: passed.
- pytest: 58 tests passed.
- Branch-aware coverage: 91.94%, above the enforced 90% threshold.
- Async tests use direct ASGI transport and explicit application lifespan handling.
- The Python lockfile resolves against public PyPI URLs and passes an offline consistency check.

## Web

- ESLint: passed.
- TypeScript strict check: passed.
- Vitest: 5 tests passed, including production gateway health and fail-closed authentication regressions.
- `npm audit`: 0 known vulnerabilities in both production-only and complete dependency audits.
- Next.js 16 standalone production build: passed.
- Real API and standalone Next.js processes passed root, readiness, Basic Auth, gateway forwarding, shared-key authorization, protected-write, and schedule-validation checks.
- Standalone assets were copied to the path used by the production Docker image.

## Deployment configuration

- The API production image starts the real FastAPI application, not the diagnostic probe application.
- Both Render services bind to the platform-provided `PORT`.
- Render's web-to-API address is supplied through service discovery rather than a hardcoded public URL.
- The API persistent disk is mounted at `/data`, and all persistent application paths are descendants of that mount.
- Production runs exactly one API worker for JSON-store safety.
- Caddy sends browser and API traffic through the Next.js authorization gateway.

## Security checks

- Production write endpoints require the shared internal key.
- Browser authorization and caller-supplied internal keys are stripped before proxying.
- Telegram secrets and raw upstream failure bodies are not exposed to clients.
- Uploads are streamed, size-bounded, extension/MIME checked, signature checked, and stored under generated names.
- Every schedule requires an explicit timezone-aware start timestamp, preventing accidental immediate publication.
- Published and delivery-uncertain history is protected from destructive mutation.

## Environment limitation

No Docker daemon is available in this execution environment. Dockerfiles and Compose/Blueprint configuration were statically checked, while API tests, frontend checks, a standalone Next.js build, dependency audits, and real-process HTTP integration were run without Docker.
