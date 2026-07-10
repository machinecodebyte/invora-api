# Project Runner

Follow these steps from the `backend/` directory.

Supported run modes:

1. Local Unix/macOS/Linux with `python3 -m ...`
2. Local Windows with `py -3 -m ...`
3. Docker-only mode with `docker compose exec backend python -m ...`

## 1. Create the Environment File

```powershell
Copy-Item .env.example .env
```

Review `.env` and keep secrets out of source control. `JWT_SECRET_KEY` must be
changed before any shared or deployed environment.

## 2. Install Dependencies

```powershell
python3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python3 -m pip install --upgrade pip
python3 -m pip install -e ".[dev]"
```

Windows launcher alternative:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
py -3 -m pip install --upgrade pip
py -3 -m pip install -e ".[dev]"
```

## 3. Check Local Ports

This machine may have other projects running. Check ports before starting
Docker services:

```powershell
Get-NetTCPConnection -LocalPort 5432 -ErrorAction SilentlyContinue
Get-NetTCPConnection -LocalPort 56379 -ErrorAction SilentlyContinue
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
docker ps
```

Do not kill existing processes. If `5432` is busy, choose an available
PostgreSQL host port such as `5433`, `55432`, or `55433`. If `6379` is busy,
choose an available Redis host port such as `6380`, `56379`, or `56380`.

The current safe local defaults use PostgreSQL host port `5432` and Redis host
port `56379`, with backend host port `8000`. Update `.env` to match your
selected host ports:

```text
POSTGRES_HOST_PORT=5433
REDIS_HOST_PORT=56380
BACKEND_HOST_PORT=8001
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

Docker-only backend mode:

```powershell
docker compose up -d invora-postgres invora-redis backend
```

Check service health:

```powershell
docker compose ps
```

Expected isolated Docker resources:

```text
project: invora
services: backend, invora-postgres, invora-redis
containers: invora-backend, invora-postgres, invora-redis
network: invora-network
volumes: invora-postgres-data, invora-redis-data
```

## 5. Run Migrations

```powershell
python3 -m alembic upgrade head
python3 -m alembic current
```

Windows launcher alternative:

```powershell
py -3 -m alembic upgrade head
py -3 -m alembic current
```

Docker-only migration:

```powershell
docker compose exec backend python -m alembic upgrade head
docker compose exec backend python -m alembic current
```

The Auth migration creates `users` and `auth_refresh_tokens`. The User Profile
migration adds safe nullable profile fields to `users`. The Product Catalog
migration creates `product_categories` and `products` with user-scoped unique
category names and SKUs. The Inventory migration creates `inventory_items` and
`inventory_stock_movements` so stock changes are tracked through a movement
ledger. The Sales Upload migration creates upload batches, sales transactions,
and rejected row tables for historical demand ingestion. The Sales Transactions
migration adds soft-delete fields and query indexes to the existing
`sales_transactions` table. The Forecast Run migration creates
`forecast_runs` for lifecycle metadata. The ML Forecasting migration creates
`forecast_predictions` and `forecast_model_metrics` for generated predictions
and model quality summaries. The Reorder Recommendations migration creates
`reorder_recommendations` for persisted reorder decisions generated from
completed forecast predictions and inventory snapshots.

## 6. Start FastAPI

```powershell
python3 -m uvicorn app.main:app --reload
```

Windows launcher alternative:

```powershell
py -3 -m uvicorn app.main:app --reload
```

Docker-only backend is started with:

```powershell
docker compose up -d backend
```

API root:

```text
http://127.0.0.1:8000
```

Swagger UI:

```text
http://127.0.0.1:8000/docs
http://127.0.0.1:8000/redoc
http://127.0.0.1:8000/openapi.json
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

Use the returned product id to verify Inventory APIs. Thresholds can be patched
on the inventory item, but stock quantities must be changed through movement
ledger calls:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/api/v1/inventory/items `
  -Headers @{ Authorization = "Bearer <token>" } `
  -ContentType "application/json" `
  -Body '{"product_id":"<product_id>","opening_stock":"10.000","minimum_stock":"5.000"}'

Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/api/v1/inventory/movements `
  -Headers @{ Authorization = "Bearer <token>" } `
  -ContentType "application/json" `
  -Body '{"product_id":"<product_id>","movement_type":"stock_in","quantity":"2.000"}'
```

Verify Sales Upload with a CSV file. This stores historical demand data only;
it does not reduce inventory stock:

```powershell
Set-Content -LiteralPath .\sales-sample.csv -Value @"
sale_date,product_sku,quantity,unit_price,total_amount,customer_name,channel,notes
2026-07-01,MILK-1,2.000,12.50,,Walk-in,store,Historical sale
"@

curl.exe -X POST `
  http://127.0.0.1:8000/api/v1/sales/uploads `
  -H "Authorization: Bearer <token>" `
  -F "file=@sales-sample.csv;type=text/csv"
```

Verify Sales Transactions with the same Bearer access token. This manages and
aggregates cleaned demand rows only; it does not reduce inventory stock:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/api/v1/sales/transactions `
  -Headers @{ Authorization = "Bearer <token>" } `
  -ContentType "application/json" `
  -Body '{"product_id":"<product_id>","sale_date":"2026-07-01","quantity":"2.000","unit_price":"12.50","channel":"store"}'

Invoke-RestMethod `
  -Headers @{ Authorization = "Bearer <token>" } `
  http://127.0.0.1:8000/api/v1/sales/transactions/summary
```

Verify Forecast Runs with the same Bearer access token. This creates pending
run metadata. ML Forecasting can then process a pending or failed run:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/api/v1/forecast-runs `
  -Headers @{ Authorization = "Bearer <token>" } `
  -ContentType "application/json" `
  -Body '{"horizon_days":7}'

Invoke-RestMethod `
  -Headers @{ Authorization = "Bearer <token>" } `
  http://127.0.0.1:8000/api/v1/forecast-runs/options
```

Verify ML Forecasting with the returned forecast run id:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri 'http://127.0.0.1:8000/api/v1/forecast-runs/<run_id>/process' `
  -Headers @{ Authorization = "Bearer <token>" }

Invoke-RestMethod `
  -Headers @{ Authorization = "Bearer <token>" } `
  http://127.0.0.1:8000/api/v1/ml/forecasting/health
```

Verify Forecast Results after the run has completed processing:

```powershell
Invoke-RestMethod `
  -Headers @{ Authorization = "Bearer <token>" } `
  'http://127.0.0.1:8000/api/v1/forecast-results/runs/<run_id>'

Invoke-RestMethod `
  -Headers @{ Authorization = "Bearer <token>" } `
  'http://127.0.0.1:8000/api/v1/forecast-results/runs/<run_id>/predictions'

Invoke-RestMethod `
  -Headers @{ Authorization = "Bearer <token>" } `
  'http://127.0.0.1:8000/api/v1/forecast-results/runs/<run_id>/chart?interval=day'
```

Verify Reorder Recommendations after Forecast Results are available and each
forecasted product has an Inventory item:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri 'http://127.0.0.1:8000/api/v1/recommendations/runs/<run_id>/generate' `
  -Headers @{ Authorization = "Bearer <token>" } `
  -ContentType "application/json" `
  -Body '{"refresh":false}'

Invoke-RestMethod `
  -Headers @{ Authorization = "Bearer <token>" } `
  'http://127.0.0.1:8000/api/v1/recommendations/runs/<run_id>/summary'
```

Recommendation generation reads Forecast Results and Inventory snapshots. It
does not update stock quantities, change forecast run status, or create
purchase orders.

Verify Dashboard Analytics with the same Bearer access token:

```powershell
Invoke-RestMethod `
  -Headers @{ Authorization = "Bearer <token>" } `
  'http://127.0.0.1:8000/api/v1/dashboard/summary'

Invoke-RestMethod `
  -Headers @{ Authorization = "Bearer <token>" } `
  'http://127.0.0.1:8000/api/v1/dashboard/demand-trends?interval=week'

Invoke-RestMethod `
  -Headers @{ Authorization = "Bearer <token>" } `
  'http://127.0.0.1:8000/api/v1/dashboard/reorder-alerts'
```

Dashboard Analytics is read-only. It combines existing Products, Inventory,
Sales, Forecast, and Recommendation data and does not create reports or mutate
business records.
