# Folder structure

```text
kalibr-publisher/
├── .github/workflows/          Continuous-integration pipelines
├── apps/
│   ├── api/                    FastAPI service
│   │   ├── src/kalibr_publisher/
│   │   │   ├── api/            HTTP routing
│   │   │   ├── core/           Configuration, logging, middleware and runtime checks
│   │   │   ├── schemas/        Typed API response models
│   │   │   └── main.py         Application factory and lifespan
│   │   ├── tests/              API unit and integration tests
│   │   ├── Dockerfile          Development and production API image
│   │   ├── pyproject.toml      Python dependencies and quality-tool configuration
│   │   └── uv.lock             Reproducible Python dependency lock
│   └── web/                    Next.js application
│       ├── app/                App Router pages and route handlers
│       ├── components/         Reusable application and UI components
│       ├── lib/                API client, localization and shared helpers
│       ├── messages/           Uzbek and Russian dictionaries
│       ├── public/             Static public assets
│       ├── Dockerfile          Development and production web image
│       └── package.json        Frontend commands and dependencies
├── infrastructure/caddy/       HTTPS and reverse-proxy configuration
├── docs/                       Architecture, installation and operating guides
├── backups/                    Runtime backup volume mount
├── logs/                       Runtime log volume mount
├── storage/                    Runtime uploaded-media volume mount
├── tmp/                        Controlled runtime temporary workspace
├── docker-compose.yml          Local development stack
├── docker-compose.production.yml Standalone production stack
├── Makefile                    Repeatable engineering and operations commands
├── package.json                Monorepo workspace and shared dependency policy
└── README.md                   Project entry point
```

Generated or machine-local directories such as `node_modules`, `.venv`, `.next`, cache directories, coverage data and `.env` are excluded from source archives and version control.
