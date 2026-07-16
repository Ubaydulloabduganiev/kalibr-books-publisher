# Installation guide

## Recommended: Docker development environment

### Prerequisites

- Docker Engine 26 or newer
- Docker Compose v2
- Git

### Install

```bash
git clone <private-repository-url> kalibr-publisher
cd kalibr-publisher
cp .env.example .env
docker compose up --build
```

The development services are then available at:

- Web interface: `http://localhost:3000`
- FastAPI documentation: `http://localhost:8000/docs`
- API readiness: `http://localhost:8000/api/v1/health/ready`

Stop the services without removing persistent data:

```bash
docker compose down
```

## Native development environment

Use native installation only when Docker is unsuitable for local debugging.

### Prerequisites

- Python 3.12
- uv 0.11.28 or newer
- Node.js 22
- npm 10

### Install dependencies

```bash
cp .env.example .env
make bootstrap
```

### Run the API

```bash
make api-dev
```

### Run the web application

In a second terminal:

```bash
make web-dev
```

### Validate the installation

```bash
make check
npm run web:build
```

Production installation is documented in [`deployment.md`](deployment.md).
