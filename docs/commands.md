# Commands

Run commands from `backend/`.

## Install

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

## Environment

```powershell
Copy-Item .env.example .env
```

## Port Checks

```powershell
Get-NetTCPConnection -LocalPort 5432 -ErrorAction SilentlyContinue
Get-NetTCPConnection -LocalPort 56379 -ErrorAction SilentlyContinue
docker ps
```

Current safe local defaults use `POSTGRES_HOST_PORT=5432` and
`REDIS_HOST_PORT=56379`. If a port is busy, set `POSTGRES_HOST_PORT` or
`REDIS_HOST_PORT` in `.env` and update local `DATABASE_URL` or `REDIS_URL` to
use the selected host port.

## Docker Compose

```powershell
docker compose config
docker compose up -d invora-postgres invora-redis
docker compose ps
docker compose logs invora-postgres
docker compose logs invora-redis
docker compose down
```

Invora Docker resources are isolated as:

```text
project: invora
services: invora-postgres, invora-redis
containers: invora-postgres, invora-redis
network: invora-network
volumes: invora-postgres-data, invora-redis-data
```

Do not use `docker compose down -v`, `docker volume rm`, `docker system prune`,
or forced container removal unless you explicitly intend to remove local data.

## Run Server

```powershell
uvicorn app.main:app --reload
```

## Alembic

```powershell
alembic heads
alembic current
alembic upgrade head
alembic revision --autogenerate -m "describe change"
alembic downgrade -1
```

## Tests

```powershell
python -m pytest
```

Run auth tests only:

```powershell
python -m pytest app/tests/unit/test_auth_passwords.py app/tests/unit/test_auth_tokens.py app/tests/unit/test_auth_service.py app/tests/integration/test_auth_api.py
```

Run user profile tests only:

```powershell
python -m pytest app/tests/unit/test_user_profile.py app/tests/integration/test_user_profile_api.py
```

Run product catalog tests only:

```powershell
python -m pytest app/tests/unit/test_products.py app/tests/integration/test_products_api.py
```

Run inventory tests only:

```powershell
python -m pytest app/tests/unit/test_inventory.py app/tests/integration/test_inventory_api.py
```

Run sales upload tests only:

```powershell
python -m pytest app/tests/unit/test_sales_upload.py app/tests/integration/test_sales_upload_api.py
```

Run health tests:

```powershell
python -m pytest app/tests/integration/test_health_api.py
```

## Lint

```powershell
ruff check .
```

## Format

```powershell
ruff format .
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

Browser URLs:

```text
http://127.0.0.1:8000/docs
http://127.0.0.1:8000/redoc
```
