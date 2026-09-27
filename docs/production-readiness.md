# Production Readiness

## Verified Locally

- The full backend suite passes, database migrations have one head, and
  `alembic check` reports no pending schema operations.
- Compose configuration validates and Invora resources use the dedicated
  `invora` project, `invora-network`, and named Invora volumes.
- PostgreSQL, Redis, FastAPI readiness, Swagger, and the RQ worker were
  verified in the local compose environment.

## Required Before Staging

- Set `APP_ENV=production` and `DEBUG=false`.
- Use a unique high-entropy `JWT_SECRET_KEY` and PostgreSQL credentials from a
  secret manager. Compose now reads PostgreSQL values from untracked `.env`;
  migrate an existing volume carefully before changing its database credential.
- Add a lock file with reviewed dependency versions and CI checks for Ruff,
  pytest, dependency vulnerabilities, and Alembic schema drift.
- Deploy behind HTTPS with rate limiting and an ingress upload-size limit.
- Add container health/restart policy appropriate for the target platform and
  monitoring for FastAPI errors, PostgreSQL, Redis, and RQ queue depth.

## Readiness Decision

The backend is ready for local frontend integration and a controlled demo. It
is not staging-ready until the secret, dependency, edge-security, and
observability items above are completed.

## Final hardening update

The dependency-lock, worker-readiness, migration-order, port-binding, and
application auth-rate-limit findings are resolved and have test coverage. The
final backend suite passed 336 collected tests with zero failures/errors.

The service is ready for controlled staging only after deployment-specific
secrets, TLS/ingress configuration, automated vulnerability scanning,
observability/alerting, backup/restore verification, and managed-service
operational ownership are supplied. Those concerns cannot be certified from a
local repository and disposable Compose run.
