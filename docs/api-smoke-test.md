# API Smoke Test

Run this from `backend/` against a disposable local environment. The workflow
creates business records, so do not use a shared production database.

## Start and Verify Runtime

```powershell
docker compose config
docker compose up -d invora-postgres invora-redis backend invora-worker
docker compose exec backend python -m alembic upgrade head
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health/ready
```

Both health responses should return `{ success: true, data: { status: ... } }`.
Open `http://127.0.0.1:8000/docs` to confirm Swagger UI is reachable.

## Authenticate

Register a throwaway user in Swagger, then copy the returned access token:

```text
POST /api/v1/auth/register
{
  "email": "smoke@example.test",
  "password": "StrongPass1!",
  "full_name": "Smoke User"
}
```

The response has `data.user` and `data.tokens`. Click **Authorize** in Swagger
and enter `Bearer <access_token>`. `GET /api/v1/auth/me` should return `200`.

## Product and Inventory

1. `POST /api/v1/products/categories` with `{ "name": "Smoke" }`.
2. `POST /api/v1/products` with a unique SKU, unit, and selling price.
3. `POST /api/v1/inventory/items` with the new `product_id`, opening stock,
   minimum stock, and safety stock.
4. `POST /api/v1/inventory/movements` with `movement_type: "stock_in"` or
   `"stock_out"` and a positive `quantity`.

Each creation returns `201` and the movement response includes updated balance
data. Do not attempt to patch `current_stock`: stock changes are ledger-only.

## Sales and Forecasting

1. Upload a CSV through `POST /api/v1/sales/uploads`, using the documented
   `sale_date,product_sku,quantity` columns.
2. Confirm the accepted rows through `GET /api/v1/sales/transactions` and a
   summary through `GET /api/v1/sales/transactions/summary`.
3. Create a pending run with `POST /api/v1/forecast-runs`.
4. Either process it synchronously through
   `POST /api/v1/forecast-runs/{run_id}/process` or enqueue it through
   `POST /api/v1/jobs/forecast-runs/{run_id}`.
5. For queued work, poll `GET /api/v1/jobs/{job_id}` until its status is
   `completed` or `failed`.

Sales data supplies historical demand only; it must not reduce inventory.

## Results, Recommendations, and Read APIs

After a completed run, verify these authenticated endpoints return `200`:

```text
GET  /api/v1/forecast-results/runs/{run_id}
GET  /api/v1/forecast-results/runs/{run_id}/predictions
GET  /api/v1/forecast-results/runs/{run_id}/metrics
POST /api/v1/recommendations/runs/{run_id}/generate
GET  /api/v1/recommendations/runs/{run_id}/summary
GET  /api/v1/dashboard/summary
GET  /api/v1/reports/sales-summary
GET  /api/v1/settings
```

Recommendations and dashboard/report endpoints read existing forecast,
inventory, and sales data. Settings responses contain user preferences only;
they never return deployment secrets.

## Runtime Checks

```powershell
docker compose ps
docker compose logs --tail 80 backend
docker compose logs --tail 80 invora-worker
docker compose exec invora-postgres pg_isready -U postgres -d invora
docker compose exec invora-redis redis-cli ping
```

Expected services are `invora-backend`, `invora-worker`, `invora-postgres`, and
`invora-redis`, all attached to `invora-network`.
