# Installation guide

## Docker development environment

### Requirements

- Docker Engine with Docker Compose v2
- Git

### Install and start

```bash
git clone <private-repository-url> kalibr-publisher
cd kalibr-publisher
cp .env.example .env
```

Before exposing the application, change at least:

```dotenv
INTERNAL_API_KEY=<long random value>
ADMIN_BASIC_PASSWORD=<strong password>
```

Then start:

```bash
docker compose up --build
```

Open:

- Web: `http://localhost:3000`
- API root: `http://localhost:8000/`
- API docs: `http://localhost:8000/docs`
- API readiness: `http://localhost:8000/api/v1/health/ready`

Stop without deleting the named data volumes:

```bash
docker compose down
```

## Native development environment

Requirements:

- Python 3.12
- uv 0.11.28+
- Node.js 22
- npm 10+

Install dependencies:

```bash
cp .env.example .env
make bootstrap
```

Run the API:

```bash
STORAGE_ROOT=../../storage \
BACKUP_ROOT=../../backups \
TEMP_ROOT=../../tmp \
LOG_ROOT=../../logs \
make api-dev
```

Run the web application in another terminal:

```bash
API_INTERNAL_URL=http://127.0.0.1:8000 make web-dev
```

Validate:

```bash
make check
npm run web:build
```

See [`deployment.md`](deployment.md) for Render and Ubuntu VPS deployment.
