# Verification record

Run date: 13 September 2026. Environment: macOS, Python 3.12.14.

## Completed

- `python -m pytest -q`: **33 passed**, 2 dependency deprecation warnings, 0.86 seconds on the final run.
- Warnings concern Starlette's httpx test-client integration and an anyio alias; no test failed. Dependency versions are pinned to the versions actually exercised.
- Seed checked at 9 provinces, 25 districts, 25 substations, 200 installations and 134,600 readings. Foreign-key integrity check returned no violations. Repeated seed leaves data unchanged.
- Verified hierarchy, atomic resources, composite overview, latest reading, scoped/global history and district summary.
- Verified 401/403/404 isolation, provincial/district scopes, device ownership and denial of human ingestion.
- Verified creation and retrievable Location, duplicate conflict, immutable routes and database triggers, and cumulative-energy conflict.
- Verified total counts, next-page links, time filters, sort validation and page limits.
- Verified protected ETags, 304 with empty body and prevention of cache-based scope bypass.
- Verified installation provisioning, required/stale If-Match, unchanged repeated replacement and repeated deletion; history blocks deletion.
- Verified JSON media negotiation, consistent errors and OpenAPI response models/security/header documentation.
- Independently started Uvicorn and made real local HTTP requests. `/health`, `/docs`, `/openapi.json`, provinces and paginated history returned 200. Conditional installation GET returned 304 with an empty body.
- Generated `docs/openapi.json` from the running application's schema.

## Not yet verified or completed

- Public HTTPS deployment and durability across a hosted-service restart.
- Docker image execution: Docker is not installed in this environment.
- Separate module REST guidelines and marking rubric: not provided.
- Formal report, signed declaration, collaborator invitation and viva.
- National-scale throughput, formal penetration testing and production operational readiness. This is a single-instance coursework implementation, not a deployed national service.

## Repository

The supplied repository was read successfully. Its `main` branch is the Police Tuk-Tuk teaching project, at commit `4d2bcfaa387dd120b02f215ec6181d4088cd5bad` when inspected. The solar project has an independent `coursework/solar-api` branch and preserves its genuine AI-assisted build history. Publication succeeded: `git push -u origin coursework/solar-api` created the remote coursework branch. The original remote `main` was not changed. Branch URL: https://github.com/Indipa123/web-API/tree/coursework/solar-api .
