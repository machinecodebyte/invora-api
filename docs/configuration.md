# Configuration

Invora reads runtime configuration from environment variables and `.env` through
`app.core.config.Settings`. `.env` is ignored by Git; keep production values in
your deployment secret store.

## Required Runtime Values

| Variable | Purpose |
| --- | --- |
| `APP_NAME`, `APP_ENV`, `DEBUG` | Application identity and mode |
| `DATABASE_URL` | Local Python or direct hosted PostgreSQL connection |
| `REDIS_URL` | Local Python or direct hosted Redis connection |
| `JWT_SECRET_KEY` | Long, unique secret for token signing |
| `CORS_ORIGINS` | Comma-separated browser origins |
| `LOG_LEVEL` | Structured log threshold |

`APP_ENV=production` requires `DEBUG=false`. Startup configuration rejects
unsupported database and Redis schemes before SQLAlchemy or Redis is created.

## Database URL Rules

The async runtime uses `postgresql+asyncpg://`. Legacy provider URLs beginning
with `postgres://`, `postgresql://`, or `postgres+asyncpg://` are normalized in
memory to `postgresql+asyncpg://`; Invora never rewrites `.env` automatically.
Use the canonical form for new configuration.

Local Python with Docker PostgreSQL:

```text
POSTGRES_HOST_PORT=5432
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:${POSTGRES_HOST_PORT}/invora
REDIS_URL=redis://localhost:${REDIS_HOST_PORT}/0
```

Direct production runtime with hosted services:

```text
APP_ENV=production
DEBUG=false
DATABASE_URL=postgresql+asyncpg://<username>:<password>@<host>/<database>?ssl=require
REDIS_URL=rediss://<username>:<password>@<host>:<port>/0
```

For Docker, Compose injects `DOCKER_DATABASE_URL` and `DOCKER_REDIS_URL` as
the app's `DATABASE_URL` and `REDIS_URL`. Use Invora service names locally:

```text
DOCKER_DATABASE_URL=postgresql+asyncpg://postgres:postgres@invora-postgres:5432/invora
DOCKER_REDIS_URL=redis://invora-redis:6379/0
```

For a hosted production database or Redis deployment, set both the direct and
Docker values to the provider URL in `.env`; no code change is required.

### Prisma Postgres compatibility

Invora uses SQLAlchemy and Alembic, not Prisma ORM. A Prisma Postgres database
can still be the PostgreSQL provider: the application uses its pooled endpoint
for runtime traffic, while Alembic derives the documented direct endpoint when
the configured host is `pooled.db.prisma.io`.

Prisma Postgres requires an `sslmode` query parameter. Invora removes that
libpq-style parameter from the SQLAlchemy URL and supplies its value through
asyncpg's supported `ssl` connection argument. `verify-full` uses asyncpg's
system-trust SSL context, preserving certificate and hostname verification
without requiring a local libpq `root.crt` file. This keeps TLS enforcement
intact without exposing credentials or changing `.env` at runtime.

There is no `prisma/schema.prisma` or Prisma Client in this backend. Apply and
inspect the SQLAlchemy schema with Alembic and a PostgreSQL client using the
provider's direct connection string; Prisma Studio cannot discover models that
are not defined in a Prisma schema.

## API Server Settings

`API_HOST` and `API_PORT` configure the local configuration-aware launcher:

```powershell
.\.venv\Scripts\python.exe -m app.server
```

If the configured port is unavailable, the launcher tries `8000`, `8001`,
`8002`, and `8010`, and logs the selected port without exposing credentials.
For reload mode, pass the configured host and port explicitly to Uvicorn:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

Environment variables in the active shell override `.env`. Remove or correct
stale shell variables before starting a local process.

## Auth refresh-cookie settings

Browser Auth uses a refresh token only as an HttpOnly cookie. It is never
returned in the JSON Auth response and must not be configured in frontend
environment variables.

| Variable | Purpose |
| --- | --- |
| REFRESH_COOKIE_NAME | Cookie name; defaults to invora_refresh_token |
| REFRESH_COOKIE_SECURE | Explicit local/test override; production is always Secure |
| REFRESH_COOKIE_SAMESITE | lax, strict, or none; none requires Secure |
| REFRESH_COOKIE_DOMAIN | Optional shared parent domain; unset keeps the cookie host-only |

The cookie path is derived from the configured API prefix and Auth route. Login,
registration, and successful refresh set or rotate it; failed refresh and logout
clear it with matching attributes. Configure CORS_ORIGINS with explicit browser
origins and never a wildcard when browser credentials are enabled.

## Final hardening controls

`API_PORT_FALLBACK_ENABLED` is false by default and must remain false in
production. A service that cannot bind its configured port now fails instead of
silently listening elsewhere.

Authentication abuse controls are Redis-backed and enabled in production:
`AUTH_RATE_LIMIT_WINDOW_SECONDS`, the Login IP/account limits, the Register IP
limit, and the Refresh IP limit. The limiter derives HMAC-based Redis keys rather
than storing raw email addresses or IP values. Redis outages fail closed for Auth
in production and return a safe, retryable response; local/test behavior remains
explicitly configurable.

`RQ_WORKER_TTL_SECONDS` controls readiness liveness. It must exceed the worker
dequeue interval and is validated above a minimum safe value. `/health/ready`
requires a healthy database, Redis, and a live worker for the configured queues
when `WORKER_ENABLED=true`.
