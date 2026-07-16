# Phase 1 implementation record

## Decisions

- **Modular monolith:** the workload does not justify microservices, queues or Kubernetes.
- **Separate web and API containers:** independent runtime concerns without splitting business ownership.
- **Next.js App Router:** current React server-component architecture with a small client-side surface.
- **FastAPI application factory:** isolated settings and repeatable test applications.
- **Pure ASGI middleware:** avoids `BaseHTTPMiddleware` buffering and context propagation limitations.
- **Structured logs:** one JSON-compatible logging pipeline for application and Uvicorn events.
- **Real readiness:** checks actual write capability and disk capacity for every persistent directory.
- **Host bind mounts in production:** redeploying containers cannot erase uploaded content or backups.
- **Caddy:** automatic HTTPS and uncomplicated reverse proxying on one Ubuntu VPS.
- **Uzbek and Russian localization:** typed dictionaries and locale-prefixed routes from the first release.
- **No fake dashboard metrics:** Phase 1 displays only actual API and filesystem state.

## Files by responsibility

### Root

- `.env.example`: documented non-secret Phase 1 configuration.
- `docker-compose.yml`: reload-enabled development services.
- `docker-compose.production.yml`: hardened non-root production services and Caddy.
- `Makefile`: repeatable local and production commands.
- `.github/workflows/ci.yml`: API, web and container build quality gates.

### API

- `core/config.py`: validated environment settings and production invariants.
- `core/logging.py`: structured logging pipeline.
- `core/middleware.py`: request tracing, sanitized IDs, access logs and security headers.
- `core/errors.py`: consistent errors with recovery advice and no production leakage.
- `core/runtime.py`: runtime directory creation and writable probes.
- `api/routes/health.py`: liveness, readiness and non-sensitive metadata.
- `main.py`: application factory, lifespan and middleware registration.
- `tests`: configuration, health, headers, tracing and error-envelope coverage.

### Web

- `proxy.ts`: locale normalization before route handling.
- `app/layout.tsx`: language-aware root document and theme provider.
- `app/[locale]`: localized dashboard and system status routes.
- `lib/api.ts`: bounded server-to-server health requests.
- `lib/i18n.ts`: typed locale registry and dictionaries.
- `components`: reusable shadcn-style primitives and responsive shell.
- `next.config.ts`: standalone build and browser security headers.

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
