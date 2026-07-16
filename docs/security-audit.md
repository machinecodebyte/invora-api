# Security Audit Notes

This is a code and local-runtime audit baseline, not a penetration test or a
claim of production certification.

## Controls Verified

- Passwords use PBKDF2-HMAC with a per-password salt; refresh tokens are stored
  as hashes and rotated on refresh.
- JWT validation restricts the expected algorithm and validates token type and
  expiration.
- Protected module routes obtain the current user through shared dependencies;
  repository queries are user-scoped.
- SQLAlchemy expressions are used for database access. The reviewed `text()`
  uses are fixed SQL for health checks, defaults, or PostgreSQL partial-index
  definitions, not user-generated SQL.
- `CORS_ORIGINS` rejects wildcard origins because the application enables
  credentialed CORS.
- CSV exports prefix formula-like text values with an apostrophe to prevent
  spreadsheet formula execution.
- Upload validation limits CSV size, validates CSV type/encoding, and records
  rejected rows without changing inventory.
- Structured request logging records request metadata rather than request
  bodies or authorization headers.

## Remaining Deployment Work

- Replace the local PostgreSQL and JWT sample values with managed secrets
  before deployment. Do not expose PostgreSQL or Redis host ports publicly.
- Add edge rate limiting, TLS termination, and a reverse-proxy request-body
  limit that matches the application upload limit.
- Pin dependencies with a lock file and run a dependency vulnerability scanner
  in CI. `pip-audit` and `bandit` were not installed in the audited environment.
- Add real PostgreSQL/Redis end-to-end tests for a representative authenticated
  business journey in CI; most API tests intentionally use deterministic
  dependency overrides.
