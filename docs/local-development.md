# Local development

## Docker workflow

```bash
cp .env.example .env
docker compose up --build
```

Docker starts:

- `api` at `http://localhost:8000` with code reload.
- `web` at `http://localhost:3000` with Turbopack reload.
- persistent local folders mounted from `storage`, `backups`, `tmp`, and `logs`.

Inspect health:

```bash
curl http://localhost:8000/api/v1/health/live
curl http://localhost:8000/api/v1/health/ready
curl http://localhost:3000/api/health
```

Stop the stack:

```bash
docker compose down
```

## Native workflow

Requirements: Python 3.12, uv 0.11.28+, Node.js 22 and npm 10.

```bash
cp .env.example .env
make bootstrap
```

Terminal 1:

```bash
cd apps/api
uv run uvicorn kalibr_publisher.main:app --reload --no-access-log
```

Terminal 2:

```bash
npm run web:dev
```

When the web application runs natively, set `API_INTERNAL_URL=http://127.0.0.1:8000`.

## Quality gate

```bash
make check
```

This runs Ruff lint and formatting checks, strict mypy, pytest with branch coverage, ESLint, TypeScript strict checking, and Vitest.
