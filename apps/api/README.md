# Kalibr Publisher API

FastAPI service for manually prepared Telegram content. Version 0.1.1 includes health endpoints, protected post APIs, streamed media upload, an atomic single-process JSON store, schedule polling, and Telegram Bot API delivery.

```bash
uv sync --frozen --all-groups
uv run uvicorn kalibr_publisher.main:app --reload
uv run ruff check src tests
uv run mypy src
uv run pytest
```

Production must use exactly one API worker until the JSON store is replaced by the SQLAlchemy/Alembic database layer.
