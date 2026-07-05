# Invora

Predict - Optimize - Replenish

Invora is an AI-based demand forecasting and inventory reorder recommendation
system for an MCA final-year capstone. This backend is a modular monolith built
with FastAPI and async SQLAlchemy.

## Implemented Modules

- Backend Foundation Module
- Auth & Identity Module
- User Profile Module
- Product Catalog Module
- Inventory Module

Pending modules include Sales Upload, Forecasting, Recommendations, Dashboard,
Reports, Background Jobs, and Settings.

## Current Scope

Implemented now:

- FastAPI application setup with API v1 routing
- Pydantic Settings configuration
- Structured JSON request logging
- Global exception handlers
- Health and readiness APIs
- User registration, login, `/me`, refresh-token rotation, and logout
- Authenticated user profile read/update and password change
- Authenticated product catalog CRUD with categories, fixed units, SKU
  normalization, user ownership, filtering, search, pagination, and soft archive
- Authenticated inventory balances, thresholds, low-stock views, summary, and
  immutable stock movement ledger for stock changes
- PBKDF2-HMAC password hashing
- HS256 access tokens and hashed refresh-token persistence
- Async SQLAlchemy 2.x setup for PostgreSQL
- Alembic migrations for foundation, auth, user profile fields, product catalog
  tables, and inventory tables
- Docker Compose services for PostgreSQL and Redis with configurable host ports
- Pytest and Ruff setup
- Swagger/OpenAPI documentation notes

## Tech Stack

- Python 3.11+
- FastAPI
- Pydantic v2 and Pydantic Settings
- SQLAlchemy 2.x async
- PostgreSQL with asyncpg
- Alembic
- Redis configuration placeholder
- Pytest, pytest-asyncio, httpx
- Ruff
- Docker Compose

## Quick Start

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

Check whether default service ports are already busy:

```powershell
Get-NetTCPConnection -LocalPort 5432 -ErrorAction SilentlyContinue
Get-NetTCPConnection -LocalPort 56379 -ErrorAction SilentlyContinue
docker ps
```

Current safe local defaults use PostgreSQL host port `5432` and Redis host port
`56379`. If needed, set different host ports in `.env`:

```text
POSTGRES_HOST_PORT=5433
REDIS_HOST_PORT=56380
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5433/invora
REDIS_URL=redis://localhost:56380/0
```

Then run:

```powershell
docker compose up -d invora-postgres invora-redis
alembic upgrade head
uvicorn app.main:app --reload
```

Verify:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health/ready
```

Swagger UI is available at:

```text
http://127.0.0.1:8000/docs
```

## Documentation

- [Docs overview](docs/README.md)
- [Run the project](docs/project-runner.md)
- [Commands](docs/commands.md)
- [Testing](docs/testing.md)
- [Architecture](docs/architecture.md)
- [Swagger/OpenAPI](docs/swagger.md)
- [Progress](docs/progress.md)

## API Summary

- Health: `/api/v1/health`, `/api/v1/health/ready`
- Auth: `/api/v1/auth/register`, `/api/v1/auth/login`, `/api/v1/auth/me`,
  `/api/v1/auth/refresh`, `/api/v1/auth/logout`
- Users: `/api/v1/users/me`, `/api/v1/users/me/change-password`
- Products: `/api/v1/products`, `/api/v1/products/{product_id}`,
  `/api/v1/products/categories`, `/api/v1/products/categories/{category_id}`,
  `/api/v1/products/units`
- Inventory: `/api/v1/inventory/items`,
  `/api/v1/inventory/items/{product_id}`, `/api/v1/inventory/movements`,
  `/api/v1/inventory/low-stock`, `/api/v1/inventory/summary`

## Next Recommended Module

Build the Sales Upload Module next. Inventory now owns stock quantities through
movement-ledger updates, which gives Sales Upload a clean stock-out integration
point.
