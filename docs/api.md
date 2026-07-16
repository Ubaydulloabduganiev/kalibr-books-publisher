# Phase 1 API documentation

FastAPI generates interactive OpenAPI documentation from the running service:

- Swagger UI: `/docs`
- ReDoc: `/redoc`
- OpenAPI JSON: `/openapi.json`

All application endpoints are versioned under `/api/v1`.

## `GET /api/v1/health/live`

Confirms that the API process is running. This endpoint does not inspect external dependencies.

Successful response:

```json
{
  "status": "ok",
  "service": "kalibr-publisher-api",
  "version": "0.1.0"
}
```

## `GET /api/v1/health/ready`

Checks whether runtime storage, backup, temporary and log directories exist, are writable and have sufficient free space. The endpoint returns HTTP 503 when a required check fails.

## `GET /api/v1/meta`

Returns non-sensitive application metadata needed by the frontend. Secrets and filesystem paths are never included.

## Error envelope

Handled API errors use one stable structure:

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

In production, internal exception details are logged but not returned to clients.

Database-backed, authentication, media, post, scheduling and Telegram endpoints are introduced in their corresponding implementation phases rather than represented by non-working placeholders.
