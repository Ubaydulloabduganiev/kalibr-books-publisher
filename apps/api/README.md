# Kalibr Publisher API

FastAPI service for Kalibr Publisher. Phase 1 provides the application foundation: configuration, structured logs, request tracing, standardized errors, security headers, and health endpoints.

```bash
uv sync --frozen --all-groups
uv run uvicorn kalibr_publisher.main:app --reload
uv run pytest
```
