# Deployment

## Production Configuration

Use a secret manager or deployment environment variables. At minimum set:

```text
APP_ENV=production
DEBUG=false
JWT_SECRET_KEY=<unique high-entropy secret>
DATABASE_URL=postgresql+asyncpg://<username>:<password>@<host>/<database>?ssl=require
REDIS_URL=rediss://<username>:<password>@<host>:<port>/0
CORS_ORIGINS=https://<frontend-origin>
```

For Compose with hosted services, set `DOCKER_DATABASE_URL` and
`DOCKER_REDIS_URL` to the same hosted endpoints. Do not expose PostgreSQL or
Redis ports publicly in that deployment.

## Docker Startup

```powershell
docker compose config
docker compose up -d
docker compose ps
docker compose logs --tail 80 backend
docker compose logs --tail 80 invora-worker
```

Compose uses the isolated `invora` project, `invora-network`, and Invora-named
containers and volumes. PostgreSQL, Redis, and the backend health endpoint
have health checks; the worker depends on healthy PostgreSQL and Redis.

## Runtime Checks

```text
GET /api/v1/health
GET /api/v1/health/ready
GET /docs
GET /openapi.json
GET /api/v1/jobs/health
```

Startup logs include application environment, database host/name, Redis host,
API host/port, and worker state. They do not include database passwords, Redis
credentials, or JWT secrets.
