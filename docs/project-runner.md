# Project Runner

Follow these steps from the `backend/` directory.

## 1. Create the Environment File

```powershell
Copy-Item .env.example .env
```

Review `.env` and keep secrets out of source control. `JWT_SECRET_KEY` must be
changed before any shared or deployed environment.

## 2. Install Dependencies

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

## 3. Check Local Ports

This machine may have other projects running. Check ports before starting
Docker services:

```powershell
Get-NetTCPConnection -LocalPort 5432 -ErrorAction SilentlyContinue
Get-NetTCPConnection -LocalPort 56379 -ErrorAction SilentlyContinue
docker ps
```

Do not kill existing processes. If `5432` is busy, choose an available
PostgreSQL host port such as `5433`, `55432`, or `55433`. If `6379` is busy,
choose an available Redis host port such as `6380`, `56379`, or `56380`.

The current safe local defaults use PostgreSQL host port `5432` and Redis host
port `56379`. Update `.env` to match your selected host ports:

```text
POSTGRES_HOST_PORT=5433
REDIS_HOST_PORT=56380
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5433/invora
REDIS_URL=redis://localhost:56380/0
```

For backend running locally, use `localhost:${POSTGRES_HOST_PORT}` and
`localhost:${REDIS_HOST_PORT}`.

For backend running inside Docker, service-to-service URLs must use:

```text
DATABASE_URL=postgresql+asyncpg://postgres:postgres@invora-postgres:5432/invora
REDIS_URL=redis://invora-redis:6379/0
```

## 4. Start Local Services

```powershell
docker compose config
docker compose up -d invora-postgres invora-redis
```

Check service health:

```powershell
docker compose ps
```

Expected isolated Docker resources:

```text
project: invora
services: invora-postgres, invora-redis
containers: invora-postgres, invora-redis
network: invora-network
volumes: invora-postgres-data, invora-redis-data
```

## 5. Run Migrations

```powershell
alembic upgrade head
alembic current
```

The Auth migration creates `users` and `auth_refresh_tokens`. The User Profile
migration adds safe nullable profile fields to `users`. The Product Catalog
migration creates `product_categories` and `products` with user-scoped unique
category names and SKUs.

## 6. Start FastAPI

```powershell
uvicorn app.main:app --reload
```

API root:

```text
http://127.0.0.1:8000
```

Swagger UI:

```text
http://127.0.0.1:8000/docs
```

## 7. Verify Health APIs

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health/ready
```

`/health` checks application availability. `/health/ready` also checks database
connectivity and returns a safe `503` response if PostgreSQL is unavailable.

## 8. Verify Auth APIs

Register:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/api/v1/auth/register `
  -ContentType "application/json" `
  -Body '{"email":"owner@example.com","password":"StrongPass1!","full_name":"Owner User"}'
```

Use the returned access token as `Authorization: Bearer <token>` for
`GET /api/v1/auth/me`. Use the refresh token with `POST /api/v1/auth/refresh`
and `POST /api/v1/auth/logout`.

Verify the User Profile APIs with the same Bearer access token:

```powershell
Invoke-RestMethod `
  -Headers @{ Authorization = "Bearer <token>" } `
  http://127.0.0.1:8000/api/v1/users/me
```

Verify Product Catalog APIs with the same Bearer access token:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/api/v1/products/categories `
  -Headers @{ Authorization = "Bearer <token>" } `
  -ContentType "application/json" `
  -Body '{"name":"Beverages"}'

Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/api/v1/products `
  -Headers @{ Authorization = "Bearer <token>" } `
  -ContentType "application/json" `
  -Body '{"name":"Milk","sku":"milk-1","unit":"liter","selling_price":"12.50"}'
```
