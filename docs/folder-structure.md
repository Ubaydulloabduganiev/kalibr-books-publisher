# Folder structure

```text
kalibr-publisher/
├── .github/workflows/              CI pipelines
├── apps/
│   ├── api/
│   │   ├── src/kalibr_publisher/
│   │   │   ├── api/                Dependencies and HTTP routes
│   │   │   ├── core/               Settings, errors, logging, middleware, runtime and JSON store
│   │   │   ├── integrations/       Telegram Bot API client
│   │   │   ├── schemas/            Pydantic request and response models
│   │   │   ├── services/           Scheduler and publishing orchestration
│   │   │   └── main.py             FastAPI application factory
│   │   ├── tests/                  Unit, API, scheduler and Telegram tests
│   │   ├── docker-entrypoint.py    Mounted-directory preparation and privilege drop
│   │   ├── Dockerfile              Development and production API image
│   │   ├── pyproject.toml          Python dependencies and quality configuration
│   │   └── uv.lock                 Reproducible Python lock file
│   └── web/
│       ├── app/                    Next.js App Router pages and health route
│       ├── components/             Dashboard, Telegram and scheduling UI
│       ├── lib/                    Typed API client, localization and helpers
│       ├── messages/               Uzbek and Russian dictionaries
│       ├── public/                 Static assets
│       ├── proxy.ts                Basic Auth, locale routing and API gateway
│       ├── Dockerfile              Development and standalone production image
│       └── package.json            Frontend dependencies and commands
├── infrastructure/caddy/           VPS TLS and reverse proxy
├── docs/                           Architecture and operating documentation
├── backups/                        Non-Docker/local backup directory
├── logs/                           Non-Docker/local log directory
├── tmp/                            Non-Docker/local temporary directory
├── docker-compose.yml              Docker development stack
├── docker-compose.production.yml   VPS production stack
├── render.yaml                     Render Blueprint
├── Makefile                        Engineering and operations commands
├── package.json                    npm workspace root
└── README.md                       Project entry point
```

Generated directories such as `node_modules`, `.venv`, `.next`, cache directories, coverage files, and `.env` are excluded from release archives and version control.
