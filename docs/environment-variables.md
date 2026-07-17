# Environment variables

Copy `.env.example` to `.env` for local or VPS deployment. Never commit real secrets.

## Application

| Variable | Default | Purpose |
|---|---|---|
| `APP_NAME` | `Kalibr Publisher` | Display and API service name |
| `APP_ENV` | `development` | `development`, `test`, or `production` |
| `APP_VERSION` | `0.1.1` | Displayed service version |
| `APP_DOMAIN` | `publisher.uboom.uz` | Caddy hostname |
| `APP_TIMEZONE` | `Asia/Tashkent` | Application timezone metadata |
| `APP_DEFAULT_LOCALE` | `uz` | Initial UI locale |
| `APP_SUPPORTED_LOCALES` | `uz,ru` | Comma-separated supported locales |

## API

| Variable | Default | Purpose |
|---|---|---|
| `PORT` | platform-dependent | Runtime listening port used by Docker/Render command |
| `API_HOST` | `0.0.0.0` | Native development bind address |
| `API_PORT` | `8000` | Native development port metadata |
| `API_V1_PREFIX` | `/api/v1` | API version prefix |
| `API_ALLOWED_HOSTS` | local hosts | Comma-separated trusted Host values |
| `API_CORS_ORIGINS` | `http://localhost:3000` | Comma-separated browser origins |
| `API_DOCS_ENABLED` | `true` | Enables `/docs`, `/redoc`, and `/openapi.json` |
| `API_LOG_LEVEL` | `INFO` | Python logging level |
| `API_LOG_FORMAT` | `console` | `console` or `json` |
| `API_REQUEST_ID_HEADER` | `X-Request-ID` | Request correlation header |
| `MAX_UPLOAD_MB` | `100` | Per-file upload limit |
| `SCHEDULER_POLL_SECONDS` | `15` | Due-post polling interval |
| `INTERNAL_API_KEY` | none | Shared web-to-API write authorization secret; required in production |

`INTERNAL_API_KEY` must be identical on the web and API services. Generate it with a cryptographically secure tool, for example:

```bash
openssl rand -hex 32
```

## Temporary administrator gate

| Variable | Default | Purpose |
|---|---|---|
| `ADMIN_BASIC_USERNAME` | `admin` | Temporary browser Basic Auth user |
| `ADMIN_BASIC_PASSWORD` | none | Temporary browser Basic Auth password |

When either value is absent, Basic Auth is disabled. Configure both in any internet-facing deployment. JWT authentication replaces this gate in the authentication phase.

## Persistent paths

| Variable | Container default | Purpose |
|---|---|---|
| `STORAGE_ROOT` | `/data/storage` | `posts.json` and managed media parent |
| `BACKUP_ROOT` | `/data/backups` | Backup archives |
| `TEMP_ROOT` | `/data/tmp` | Controlled temporary files |
| `LOG_ROOT` | `/data/logs` | Optional file logs and readiness probe |
| `KALIBR_DATA_DIR` | `/srv/kalibr-publisher` | VPS host root used by production Compose |

Only data under a mounted persistent path survives container replacement.

## Frontend

| Variable | Default | Purpose |
|---|---|---|
| `API_INTERNAL_URL` | `http://127.0.0.1:8000` | Server-side API origin; do not append `/api/v1` |
| `NEXT_PUBLIC_APP_NAME` | `Kalibr Publisher` | Public UI title |
| `NEXT_PUBLIC_DEFAULT_LOCALE` | `uz` | Public default locale |

In Docker development use `http://api:8000`. On Render, use the API service's private `host:port` or its HTTPS URL.

## Telegram

| Variable | Default | Purpose |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | none | BotFather token; secret |
| `TELEGRAM_DEFAULT_CHANNEL` | `@kalibr_books` | Default destination username or numeric chat ID |

The token is never returned by API metadata and must never be stored in source control.

## Caddy

| Variable | Default | Purpose |
|---|---|---|
| `CADDY_EMAIL` | none | ACME account email for HTTPS certificates |
