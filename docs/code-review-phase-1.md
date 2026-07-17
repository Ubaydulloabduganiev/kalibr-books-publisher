# Senior engineering repair review — version 0.1.1

The uploaded deployment was reviewed for functional defects, security issues, performance bottlenecks, maintainability, edge cases, and deployment reliability.

## Critical defects corrected

1. **Wrong production application:** the API image launched `boot_probe:app`; it now starts `kalibr_publisher.main:app`.
2. **Render port mismatch:** runtime commands now bind to `${PORT:-8000}` and the Blueprint uses port 10000.
3. **Broken cross-service address:** the web service receives the API private host and port through Render service discovery.
4. **Invalid Blueprint property:** unsupported `dockerfileTarget` configuration was removed; Dockerfiles use valid paths and their final production stages.
5. **Non-durable Render data:** the API stores all runtime state below the mounted `/data` disk.
6. **Confusing API root:** `/` now returns service and health metadata instead of 404.
7. **AI scope violation:** Gemini integrations, content-generation routes, parsers, UI, dependencies, and configuration were removed.
8. **Unprotected writes:** production post, upload, scheduling, deletion, and Telegram publishing routes require a shared internal service key.
9. **Gateway bypass:** Caddy routes only to Next.js so the temporary administrator gate cannot be bypassed on VPS deployment.
10. **Secret forwarding:** the gateway removes browser Authorization and caller-supplied internal-key headers, then injects its trusted key.
11. **Buffered uploads:** frontend and backend now stream request bodies; backend applies a configurable size limit.
12. **Upload spoofing:** supported extensions, MIME types, and file signatures are validated before atomic storage.
13. **Path traversal:** post media must be a managed relative path below `media/`, and resolved paths are rechecked before publishing.
14. **Silent content loss:** a missing media file now fails publishing instead of sending only the caption.
15. **Telegram album multipart bug:** `attach://` references now match the actual multipart field names.
16. **Ambiguous Telegram delivery:** connection failures and uncertain post-send failures are classified separately; uncertain deliveries are not blindly retried.
17. **Non-atomic JSON persistence:** state writes now use a temporary file, flush, `fsync`, and atomic replacement.
18. **Swallowed startup failures:** unusable storage paths now fail startup/readiness rather than allowing a misleading healthy deployment.
19. **Pydantic validation serialization:** nested validation details are converted to JSON-safe values before returning error envelopes.
20. **Accidental immediate scheduling:** a one-time post now requires an explicit timezone-aware timestamp; “Send now” passes an explicit current timestamp.
21. **Frontend error leakage:** proxy failures return a controlled message and log only the error class.
22. **Hardcoded security policy host:** CSP no longer embeds the obsolete API hostname because browser API calls are same-origin.
23. **Toolchain drift:** dependency versions were aligned with the current Next.js line and the lock files were updated.
24. **CI type-check mismatch:** strict mypy runs against application source, matching the supported typing boundary.
25. **Render web health redirect:** `/api/health` bypasses locale rewriting and Basic Auth so platform health checks receive the real route response.
26. **Missing production Basic Auth:** the gateway now fails closed in production when credentials are absent instead of silently exposing the UI.
27. **Public path disclosure:** readiness responses no longer reveal mounted filesystem paths.
28. **Expected-error detail leakage:** operator diagnostics are logged but omitted from production API responses.
29. **Corrupt schedule store:** the API now fails startup when `posts.json` is unreadable instead of running with a dead scheduler.
30. **Scheduler task death:** an unexpected tick error is logged and the polling loop continues.
31. **Concurrent publication race:** posts are atomically claimed as `publishing` before Telegram is called.
32. **Unclean restart ambiguity:** in-flight records become `delivery_uncertain` on startup instead of being retried or forgotten.
33. **Mutation during delivery:** a publishing post cannot be deleted or rescheduled until its result is known.
34. **Quadratic bulk writes:** bulk creation now performs one store read and one atomic write instead of rewriting the JSON file for every post.
35. **Partial frontend bulk creation:** the UI now submits one validated bulk request instead of creating posts one by one.
36. **Immediate recurring surprise:** recurring schedules also require an explicit start time.
37. **Published-history mutation:** sent records cannot be deleted or rescheduled in place.
38. **Uncertain-delivery duplicate risk:** the UI requires explicit confirmation before manually retrying an uncertain post.
39. **Non-portable Python lockfile:** private build-environment package URLs were replaced with public PyPI/file-host URLs and the lockfile was revalidated offline.

## Accepted temporary limitations

- `posts.json` is a transitional store and supports one API process only.
- Basic Auth is a temporary deployment gate, not the planned JWT/session implementation.
- There is no durable database claim, attempt ledger, approval workflow, audit history, or production retry queue yet.
- Automatic backups and verified restore are not implemented in this repair archive.
- Caddy's static CSP permits inline scripts/styles required by the current Next.js build; nonce-based CSP belongs with the authenticated session layer.

These limitations are documented rather than hidden behind placeholder implementations.
