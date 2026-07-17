# API documentation — version 0.1.1

FastAPI exposes interactive documentation when `API_DOCS_ENABLED=true`:

- Swagger UI: `/docs`
- ReDoc: `/redoc`
- OpenAPI JSON: `/openapi.json`

Application endpoints use the `/api/v1` prefix.

## Public system endpoints

### `GET /`

Returns a small service document instead of an unexplained 404.

### `GET /api/v1/health/live`

Confirms that the API process can serve requests.

### `GET /api/v1/health/ready`

Checks the writable state and free space of storage, media, backup, temporary, and log directories. Returns HTTP 503 when a required check fails.

### `GET /api/v1/meta`

Returns non-sensitive application metadata used by the web interface.

## Protected write and post endpoints

In production these endpoints require:

```http
X-Internal-API-Key: <shared secret>
```

The browser never receives that key. The Next.js gateway injects it server-side.

### `POST /api/v1/telegram/publish`

Immediately sends a text message to the default or an explicitly supplied Telegram target.

### `POST /api/v1/posts/upload`

Streams one supported media file to managed persistent storage. The default size limit is 100 MB and is controlled by `MAX_UPLOAD_MB`.

### `POST /api/v1/posts`

Creates one scheduled manual post. Every one-time or recurring schedule must include a timezone-aware `run_at`; omitting it is rejected so a post cannot be published accidentally.

Example:

```json
{
  "text": "Yangi kitobimiz sotuvda!",
  "media": [{"kind": "photo", "path": "media/abc123.jpg"}],
  "target": "@kalibr_books",
  "parse_mode": "HTML",
  "schedule": {
    "mode": "once",
    "run_at": "2026-07-20T10:00:00+05:00"
  }
}
```

### `POST /api/v1/posts/bulk`

Creates 1–100 scheduled posts in one request.

### `GET /api/v1/posts`

Lists posts. Optional query: `?status=pending`.

### `GET /api/v1/posts/{post_id}`

Returns one post.

### `POST /api/v1/posts/{post_id}/schedule`

Changes a schedule. The web interface uses an explicit current UTC timestamp for “Send now.” Posts currently being published cannot be rescheduled, and already published posts must be duplicated rather than mutated in place.

### `DELETE /api/v1/posts/{post_id}`

Deletes a pending or failed post record from the current JSON store. Publishing, published, and delivery-uncertain records are protected because they form part of the delivery history.

## Error envelope

Handled errors use one stable structure:

```json
{
  "error": {
    "code": "machine_readable_code",
    "message": "Readable explanation",
    "technical_details": null,
    "recovery_suggestion": "Action the operator can take",
    "request_id": "traceable-request-id"
  }
}
```

Production responses do not expose stack traces, Telegram tokens, filesystem paths, or upstream error bodies.
