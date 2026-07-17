# Local development

## Docker workflow

```bash
cp .env.example .env
# Set a non-default INTERNAL_API_KEY and ADMIN_BASIC_PASSWORD.
docker compose up --build
```

Services:

- API: `http://localhost:8000`
- Web: `http://localhost:3000`
- API docs: `http://localhost:8000/docs`

The development API uses the named Docker volume `api-data`. This avoids host UID/GID problems while preserving media and `posts.json` across normal container recreation.

Inspect health:

```bash
curl http://localhost:8000/
curl http://localhost:8000/api/v1/health/live
curl http://localhost:8000/api/v1/health/ready
curl http://localhost:3000/api/health
```

Stop:

```bash
docker compose down
```

To intentionally delete local Docker data:

```bash
docker compose down -v
```

## Native workflow

Requirements: Python 3.12, uv 0.11.28+, Node.js 22, and npm 10.

```bash
cp .env.example .env
make bootstrap
```

For native API development, update paths in `.env` to writable local paths or export them before launch.

Terminal 1:

```bash
cd apps/api
STORAGE_ROOT=../../storage \
BACKUP_ROOT=../../backups \
TEMP_ROOT=../../tmp \
LOG_ROOT=../../logs \
uv run uvicorn kalibr_publisher.main:app --reload --no-access-log
```

Terminal 2:

```bash
API_INTERNAL_URL=http://127.0.0.1:8000 npm run web:dev
```

## Quality gate

```bash
make check
npm run web:build
```

The gate runs Ruff, formatting checks, strict mypy on application source, pytest with branch coverage, ESLint, TypeScript checking, and Vitest.
