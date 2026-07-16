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
