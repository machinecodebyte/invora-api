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
- Sales Upload Module
- Sales Transactions Module
- Forecast Run Module
- ML Forecasting Module
- Forecast Results Module
- Reorder Recommendations Module

Pending modules include Dashboard Analytics, Reports, Background Jobs, and
Settings.

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
- Authenticated sales CSV upload with batch tracking, row-level validation,
  accepted sales transactions, rejected rows, and duplicate file protection
- Authenticated sales transaction create/list/detail/update/soft-delete APIs,
  filtering, summaries, trends, and product-wise aggregates over cleaned sales
  data
- Authenticated forecast run lifecycle APIs for pending run creation, list,
  detail, cancellation, options, and pre-flight sales/product data validation
- Authenticated ML forecasting processing for pending/failed forecast runs,
  deterministic Random Forest training, recent-average fallback for sparse
  products, persisted predictions, persisted metrics, options, and health APIs
- Authenticated forecast result APIs for run overview, paginated product/date
  predictions, metrics, chart data, and product-level forecast detail
- Authenticated reorder recommendation APIs for completed forecast runs,
  forecast-demand aggregation, inventory snapshot comparison, reorder quantity,
  risk level, refresh, summaries, and acknowledge/dismiss status updates
- PBKDF2-HMAC password hashing
- HS256 access tokens and hashed refresh-token persistence
- Async SQLAlchemy 2.x setup for PostgreSQL
- Alembic migrations for foundation, auth, user profile fields, product catalog
  tables, inventory tables, sales upload tables, and sales transaction
  soft-delete/query fields, forecast run lifecycle tables, and ML forecasting
  prediction/metric tables, and reorder recommendation tables
- Docker Compose services for PostgreSQL and Redis with configurable host ports
- pandas, numpy, and scikit-learn for local ML forecasting
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

Use `python3 -m ...` on Unix/macOS/Linux. On Windows, use `py -3 -m ...` if
`python` is unavailable. Inside Docker, `python` is available in the backend
container.

```powershell
cd backend
python3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python3 -m pip install --upgrade pip
python3 -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

Windows launcher alternative:

```powershell
py -3 -m venv .venv
py -3 -m pip install --upgrade pip
py -3 -m pip install -e ".[dev]"
```

Check whether default service ports are already busy:

```powershell
Get-NetTCPConnection -LocalPort 5432 -ErrorAction SilentlyContinue
Get-NetTCPConnection -LocalPort 56379 -ErrorAction SilentlyContinue
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
docker ps
```

Current safe local defaults use PostgreSQL host port `5432` and Redis host port
`56379`, with backend host port `8000`. If needed, set different host ports in
`.env`:

```text
POSTGRES_HOST_PORT=5433
REDIS_HOST_PORT=56380
BACKEND_HOST_PORT=8001
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5433/invora
REDIS_URL=redis://localhost:56380/0
```

Then run:

```powershell
docker compose up -d invora-postgres invora-redis
python3 -m alembic upgrade head
python3 -m uvicorn app.main:app --reload
```

Docker-only backend path:

```powershell
docker compose up -d invora-postgres invora-redis backend
docker compose exec backend python -m alembic upgrade head
docker compose exec backend python -m pytest
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
- Sales Upload: `/api/v1/sales/uploads`,
  `/api/v1/sales/uploads/{upload_id}`,
  `/api/v1/sales/uploads/{upload_id}/rejected-rows`,
  `/api/v1/sales/uploads/template`
- Sales Transactions: `/api/v1/sales/transactions`,
  `/api/v1/sales/transactions/summary`,
  `/api/v1/sales/transactions/trends`,
  `/api/v1/sales/transactions/by-product`,
  `/api/v1/sales/transactions/{transaction_id}`
- Forecast Runs: `/api/v1/forecast-runs`,
  `/api/v1/forecast-runs/options`, `/api/v1/forecast-runs/{run_id}`,
  `/api/v1/forecast-runs/{run_id}/process`,
  `/api/v1/forecast-runs/{run_id}/cancel`
- ML Forecasting: `/api/v1/ml/forecasting/options`,
  `/api/v1/ml/forecasting/health`
- Forecast Results: `/api/v1/forecast-results/runs/{run_id}`,
  `/api/v1/forecast-results/runs/{run_id}/predictions`,
  `/api/v1/forecast-results/runs/{run_id}/metrics`,
  `/api/v1/forecast-results/runs/{run_id}/chart`,
  `/api/v1/forecast-results/runs/{run_id}/products/{product_id}`
- Reorder Recommendations:
  `/api/v1/recommendations/runs/{run_id}/generate`,
  `/api/v1/recommendations`,
  `/api/v1/recommendations/runs/{run_id}`,
  `/api/v1/recommendations/runs/{run_id}/summary`,
  `/api/v1/recommendations/{recommendation_id}`,
  `/api/v1/recommendations/{recommendation_id}/status`

## Next Recommended Module

Build the Dashboard Analytics Module next. Reorder Recommendations now expose
reorder risk, top reorder products, and forecast-run summaries that can feed
dashboard KPIs and risk cards.
