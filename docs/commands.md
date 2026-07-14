# Commands

Run commands from `backend/`.

Use `python3 -m ...` on Unix/macOS/Linux. On Windows, use `py -3 -m ...`
when the `python` command is unavailable. Inside the Docker backend container,
`python` is available.

## Install

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

## Environment

```powershell
Copy-Item .env.example .env
```

## Port Checks

```powershell
Get-NetTCPConnection -LocalPort 5432 -ErrorAction SilentlyContinue
Get-NetTCPConnection -LocalPort 56379 -ErrorAction SilentlyContinue
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
docker ps
```

Current safe local defaults use `POSTGRES_HOST_PORT=5432` and
`REDIS_HOST_PORT=56379`, with backend host port `BACKEND_HOST_PORT=8000`. If a
port is busy, set `POSTGRES_HOST_PORT`, `REDIS_HOST_PORT`, or
`BACKEND_HOST_PORT` in `.env`. For local Python runs, update `DATABASE_URL` and
`REDIS_URL` to use the selected host ports.

## Docker Compose

```powershell
docker compose config
docker compose up -d invora-postgres invora-redis
docker compose up -d backend
docker compose ps
docker compose logs backend
docker compose logs invora-postgres
docker compose logs invora-redis
docker compose down
```

Invora Docker resources are isolated as:

```text
project: invora
services: backend, invora-postgres, invora-redis
containers: invora-backend, invora-postgres, invora-redis
network: invora-network
volumes: invora-postgres-data, invora-redis-data
```

Do not use `docker compose down -v`, `docker volume rm`, `docker system prune`,
or forced container removal unless you explicitly intend to remove local data.

## Run Server

```powershell
python3 -m uvicorn app.main:app --reload
```

Windows launcher alternative:

```powershell
py -3 -m uvicorn app.main:app --reload
```

Docker-only backend:

```powershell
docker compose up -d invora-postgres invora-redis backend
docker compose exec backend python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Alembic

```powershell
python3 -m alembic heads
python3 -m alembic current
python3 -m alembic upgrade head
python3 -m alembic revision --autogenerate -m "describe change"
python3 -m alembic downgrade -1
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

## Tests

```powershell
python3 -m pytest
```

Windows launcher alternative:

```powershell
py -3 -m pytest
```

Docker-only tests:

```powershell
docker compose exec backend python -m pytest
```

Run auth tests only:

```powershell
python3 -m pytest app/tests/unit/test_auth_passwords.py app/tests/unit/test_auth_tokens.py app/tests/unit/test_auth_service.py app/tests/integration/test_auth_api.py
```

Run user profile tests only:

```powershell
python3 -m pytest app/tests/unit/test_user_profile.py app/tests/integration/test_user_profile_api.py
```

Run product catalog tests only:

```powershell
python3 -m pytest app/tests/unit/test_products.py app/tests/integration/test_products_api.py
```

Run inventory tests only:

```powershell
python3 -m pytest app/tests/unit/test_inventory.py app/tests/integration/test_inventory_api.py
```

Run sales upload tests only:

```powershell
python3 -m pytest app/tests/unit/test_sales_upload.py app/tests/integration/test_sales_upload_api.py
```

Run sales transaction tests only:

```powershell
python3 -m pytest app/tests/unit/test_sales_transactions.py app/tests/integration/test_sales_transactions_api.py
```

Run forecast run tests only:

```powershell
python3 -m pytest app/tests/unit/test_forecast_runs.py app/tests/integration/test_forecast_runs_api.py
```

Run ML forecasting tests only:

```powershell
python3 -m pytest app/tests/unit/test_ml_forecasting_pipeline.py app/tests/integration/test_ml_forecasting_api.py
```

Run forecast result tests only:

```powershell
python3 -m pytest app/tests/unit/test_forecast_results.py app/tests/integration/test_forecast_results_api.py
```

Run reorder recommendation tests only:

```powershell
python3 -m pytest app/tests/unit/test_recommendations.py app/tests/integration/test_recommendations_api.py
```

Run dashboard analytics tests only:

```powershell
python3 -m pytest app/tests/unit/test_dashboard.py app/tests/integration/test_dashboard_api.py
```

Run reports tests only:

```powershell
python3 -m pytest app/tests/unit/test_reports.py app/tests/integration/test_reports_api.py
```

Run health tests:

```powershell
python3 -m pytest app/tests/integration/test_health_api.py
```

## Lint

```powershell
python3 -m ruff check .
```

## Format

```powershell
python3 -m ruff format .
```

## Swagger/OpenAPI Verification

```powershell
Invoke-RestMethod http://127.0.0.1:8000/openapi.json
```

Manual protected API check:

```powershell
# Register or login, copy data.tokens.access_token, then call:
Invoke-RestMethod `
  -Headers @{ Authorization = "Bearer <access_token>" } `
  http://127.0.0.1:8000/api/v1/users/me
```

Manual product API check:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/api/v1/products/categories `
  -Headers @{ Authorization = "Bearer <access_token>" } `
  -ContentType "application/json" `
  -Body '{"name":"Beverages"}'

Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/api/v1/products `
  -Headers @{ Authorization = "Bearer <access_token>" } `
  -ContentType "application/json" `
  -Body '{"name":"Milk","sku":"milk-1","unit":"liter","selling_price":"12.50"}'
```

Manual inventory API check:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/api/v1/inventory/items `
  -Headers @{ Authorization = "Bearer <access_token>" } `
  -ContentType "application/json" `
  -Body '{"product_id":"<product_id>","opening_stock":"10.000","minimum_stock":"5.000","safety_stock":"2.000"}'

Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/api/v1/inventory/movements `
  -Headers @{ Authorization = "Bearer <access_token>" } `
  -ContentType "application/json" `
  -Body '{"product_id":"<product_id>","movement_type":"stock_out","quantity":"1.000","reason":"Manual sale"}'
```

Manual sales upload API check:

```powershell
Set-Content -LiteralPath .\sales-sample.csv -Value @"
sale_date,product_sku,quantity,unit_price,total_amount,customer_name,channel,notes
2026-07-01,MILK-1,2.000,12.50,,Walk-in,store,Historical sale
"@

curl.exe -X POST `
  http://127.0.0.1:8000/api/v1/sales/uploads `
  -H "Authorization: Bearer <access_token>" `
  -F "file=@sales-sample.csv;type=text/csv"
```

Manual sales transaction API check:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/api/v1/sales/transactions `
  -Headers @{ Authorization = "Bearer <access_token>" } `
  -ContentType "application/json" `
  -Body '{"product_id":"<product_id>","sale_date":"2026-07-01","quantity":"2.000","unit_price":"12.50","channel":"store"}'

Invoke-RestMethod `
  -Headers @{ Authorization = "Bearer <access_token>" } `
  'http://127.0.0.1:8000/api/v1/sales/transactions/summary'

Invoke-RestMethod `
  -Headers @{ Authorization = "Bearer <access_token>" } `
  'http://127.0.0.1:8000/api/v1/sales/transactions/trends?interval=day'
```

Manual forecast run API check:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/api/v1/forecast-runs `
  -Headers @{ Authorization = "Bearer <access_token>" } `
  -ContentType "application/json" `
  -Body '{"horizon_days":7}'

Invoke-RestMethod `
  -Headers @{ Authorization = "Bearer <access_token>" } `
  http://127.0.0.1:8000/api/v1/forecast-runs/options
```

Manual ML forecasting API check:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri 'http://127.0.0.1:8000/api/v1/forecast-runs/<run_id>/process' `
  -Headers @{ Authorization = "Bearer <access_token>" }

Invoke-RestMethod `
  -Headers @{ Authorization = "Bearer <access_token>" } `
  http://127.0.0.1:8000/api/v1/ml/forecasting/options

Invoke-RestMethod `
  -Headers @{ Authorization = "Bearer <access_token>" } `
  http://127.0.0.1:8000/api/v1/ml/forecasting/health
```

Manual forecast result API check:

```powershell
Invoke-RestMethod `
  -Headers @{ Authorization = "Bearer <access_token>" } `
  'http://127.0.0.1:8000/api/v1/forecast-results/runs/<run_id>'

Invoke-RestMethod `
  -Headers @{ Authorization = "Bearer <access_token>" } `
  'http://127.0.0.1:8000/api/v1/forecast-results/runs/<run_id>/predictions?limit=20&sort_by=forecast_date'

Invoke-RestMethod `
  -Headers @{ Authorization = "Bearer <access_token>" } `
  'http://127.0.0.1:8000/api/v1/forecast-results/runs/<run_id>/metrics'

Invoke-RestMethod `
  -Headers @{ Authorization = "Bearer <access_token>" } `
  'http://127.0.0.1:8000/api/v1/forecast-results/runs/<run_id>/chart?interval=day'

Invoke-RestMethod `
  -Headers @{ Authorization = "Bearer <access_token>" } `
  'http://127.0.0.1:8000/api/v1/forecast-results/runs/<run_id>/products/<product_id>'
```

Manual reorder recommendation API check:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri 'http://127.0.0.1:8000/api/v1/recommendations/runs/<run_id>/generate' `
  -Headers @{ Authorization = "Bearer <access_token>" } `
  -ContentType "application/json" `
  -Body '{"refresh":false}'

Invoke-RestMethod `
  -Headers @{ Authorization = "Bearer <access_token>" } `
  'http://127.0.0.1:8000/api/v1/recommendations?risk_level=high&limit=20'

Invoke-RestMethod `
  -Headers @{ Authorization = "Bearer <access_token>" } `
  'http://127.0.0.1:8000/api/v1/recommendations/runs/<run_id>/summary'

Invoke-RestMethod `
  -Method Patch `
  -Uri 'http://127.0.0.1:8000/api/v1/recommendations/<recommendation_id>/status' `
  -Headers @{ Authorization = "Bearer <access_token>" } `
  -ContentType "application/json" `
  -Body '{"status":"acknowledged"}'
```

Manual dashboard analytics API check:

```powershell
Invoke-RestMethod `
  -Headers @{ Authorization = "Bearer <access_token>" } `
  'http://127.0.0.1:8000/api/v1/dashboard/summary'

Invoke-RestMethod `
  -Headers @{ Authorization = "Bearer <access_token>" } `
  'http://127.0.0.1:8000/api/v1/dashboard/kpis'

Invoke-RestMethod `
  -Headers @{ Authorization = "Bearer <access_token>" } `
  'http://127.0.0.1:8000/api/v1/dashboard/demand-trends?interval=week'

Invoke-RestMethod `
  -Headers @{ Authorization = "Bearer <access_token>" } `
  'http://127.0.0.1:8000/api/v1/dashboard/inventory-risk'

Invoke-RestMethod `
  -Headers @{ Authorization = "Bearer <access_token>" } `
  'http://127.0.0.1:8000/api/v1/dashboard/forecast-overview'

Invoke-RestMethod `
  -Headers @{ Authorization = "Bearer <access_token>" } `
  'http://127.0.0.1:8000/api/v1/dashboard/reorder-alerts?status=open&limit=10'

Invoke-RestMethod `
  -Headers @{ Authorization = "Bearer <access_token>" } `
  'http://127.0.0.1:8000/api/v1/dashboard/recent-activity'
```

Manual reports API check:

```powershell
Invoke-RestMethod `
  -Headers @{ Authorization = "Bearer <access_token>" } `
  'http://127.0.0.1:8000/api/v1/reports/options'

Invoke-RestMethod `
  -Headers @{ Authorization = "Bearer <access_token>" } `
  'http://127.0.0.1:8000/api/v1/reports/model-performance'

Invoke-RestMethod `
  -Headers @{ Authorization = "Bearer <access_token>" } `
  'http://127.0.0.1:8000/api/v1/reports/inventory-risk'

Invoke-RestMethod `
  -Headers @{ Authorization = "Bearer <access_token>" } `
  'http://127.0.0.1:8000/api/v1/reports/reorder-summary'

Invoke-RestMethod `
  -Headers @{ Authorization = "Bearer <access_token>" } `
  'http://127.0.0.1:8000/api/v1/reports/demand-forecast?forecast_run_id=<run_id>'

Invoke-RestMethod `
  -Headers @{ Authorization = "Bearer <access_token>" } `
  'http://127.0.0.1:8000/api/v1/reports/sales-summary?date_from=2026-07-01&date_to=2026-07-31'
```

Manual reports CSV export check:

```powershell
curl.exe -L `
  -H "Authorization: Bearer <access_token>" `
  "http://127.0.0.1:8000/api/v1/reports/sales-summary?format=csv"
```

Browser URLs:

```text
http://127.0.0.1:8000/docs
http://127.0.0.1:8000/redoc
```
