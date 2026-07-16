# Senior engineering review — Phase 1

The implementation was reviewed before delivery for bugs, security, performance, maintainability, edge cases and future scale.

## Findings corrected

1. **Mutable response-model defaults:** health-check dictionaries use a factory rather than a shared mutable object.
2. **Request-ID log injection:** incoming IDs are accepted only when they match a bounded safe character set; all other values are replaced.
3. **Container data loss:** production runtime paths are host bind mounts, never writable container layers.
4. **Container privilege:** API and web images run as UID/GID 10001, use read-only root filesystems in production, drop all capabilities and set `no-new-privileges`.
5. **Error leakage:** production responses do not contain exception messages, stack traces or local paths.
6. **False readiness:** readiness writes and flushes a real temporary file and reports disk capacity instead of only checking path existence.
7. **Unbounded internal API wait:** Next.js server requests have a three-second timeout and return a controlled disconnected state.
8. **Host-header abuse:** production rejects wildcard host configuration and applies Starlette trusted-host validation.
9. **Fake operational data:** the dashboard displays live service and directory checks, not invented publishing statistics.
10. **Fragile locale handling:** unsupported locale paths are rejected and non-localized paths are redirected consistently.
11. **Environment list startup failure:** Pydantic Settings attempted JSON decoding before comma-list validation; `NoDecode` annotations and a regression test now make `.env` values such as `localhost,api` reliable.
12. **Frontend toolchain incompatibility:** ESLint 10 and TypeScript 7 were newer than the compatible Next.js plugin range; they were pinned to ESLint 9.39.5 and TypeScript 6.0.3, then fully rebuilt.
13. **Transitive CSS security advisory:** Next.js resolved an old PostCSS release; a root override pins patched PostCSS 8.5.19 and the production dependency audit now reports zero findings.
14. **Deprecated test adapter:** Starlette `TestClient` was replaced with direct async ASGI transport and explicit application lifespan handling.
15. **Compose inheritance risk:** production configuration is a standalone Compose file, preventing development source mounts and published ports from leaking into production.
16. **Reverse-proxy route collision:** Caddy now routes only `/api/v1/*` and API documentation paths to FastAPI, leaving Next.js `/api/health` reachable.
17. **Process-level integration:** Uzbek, Russian, health and redirect routes were verified with real Uvicorn and Next.js processes, not only unit tests.

## Accepted trade-offs

- The static web CSP currently permits inline scripts and styles because Next.js hydration and Tailwind styles require them without a nonce pipeline. Authentication Phase 3 will introduce per-request nonce handling before sensitive forms are enabled.
- SQLite, SQLAlchemy and Alembic are not instantiated in Phase 1 because database schema belongs to Phase 2. The container and module layout already reserve a clean database boundary without shipping unused placeholder code.
- API production uses two Uvicorn workers only for stateless Phase 1 endpoints. The scheduler will be a separate single-purpose worker in Phase 6 to prevent duplicate scheduler ownership.
