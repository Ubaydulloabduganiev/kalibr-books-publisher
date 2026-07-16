# Environment variables

All runtime configuration is supplied through environment variables. Copy `.env.example` to `.env` for local development. Never commit `.env`.

| Variable | Required | Default | Purpose |
|---|---:|---|---|
| `APP_NAME` | No | `Kalibr Publisher` | Display and API service name |
| `APP_ENV` | No | `development` | `development`, `test`, or `production` |
| `APP_VERSION` | No | `0.1.0` | Runtime release identifier |
| `APP_DOMAIN` | Production | `publisher.uboom.uz` | Caddy public hostname |
| `APP_TIMEZONE` | No | `Asia/Tashkent` | Business timezone |
| `APP_DEFAULT_LOCALE` | No | `uz` | Initial UI locale |
| `APP_SUPPORTED_LOCALES` | No | `uz,ru` | Comma-separated UI locales |
| `API_HOST` | No | `0.0.0.0` | Uvicorn bind host |
| `API_PORT` | No | `8000` | Uvicorn port |
| `API_V1_PREFIX` | No | `/api/v1` | Versioned API prefix |
| `API_ALLOWED_HOSTS` | Yes in production | local hosts | Accepted Host headers; wildcard is rejected in production |
| `API_CORS_ORIGINS` | Yes in production | local web URL | Credentialed browser origins |
| `API_DOCS_ENABLED` | No | `true` | Enable OpenAPI, Swagger UI and ReDoc |
| `API_LOG_LEVEL` | No | `INFO` | Python log threshold |
| `API_LOG_FORMAT` | No | `console` | `console` locally, `json` in production |
| `API_REQUEST_ID_HEADER` | No | `X-Request-ID` | Trace header name |
| `STORAGE_ROOT` | Yes | `/data/storage` | Original media and derivatives in later phases |
| `BACKUP_ROOT` | Yes | `/data/backups` | Backup archives |
| `TEMP_ROOT` | Yes | `/data/tmp` | Controlled temporary operations |
| `LOG_ROOT` | Yes | `/data/logs` | File logs where configured |
| `API_INTERNAL_URL` | Yes in Docker | `http://127.0.0.1:8000` | Next.js server-to-server API URL |
| `NEXT_PUBLIC_APP_NAME` | No | `Kalibr Publisher` | Public web display name |
| `NEXT_PUBLIC_DEFAULT_LOCALE` | No | `uz` | Client-visible default locale |
| `CADDY_EMAIL` | Production | none | ACME certificate contact |
| `KALIBR_DATA_DIR` | Production host | `/srv/kalibr-publisher` | Host root for persistent bind mounts |

Telegram tokens, encryption keys, JWT keys and database URLs are deliberately absent from Phase 1. They will be added with validation and secure handling in their implementation phases.
