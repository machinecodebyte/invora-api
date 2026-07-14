# Swagger and OpenAPI

## URLs

Start the backend, then open:

```text
Swagger UI: http://127.0.0.1:8000/docs
ReDoc:      http://127.0.0.1:8000/redoc
OpenAPI:   http://127.0.0.1:8000/openapi.json
```

## Authorizing With Bearer Token

1. Call `POST /api/v1/auth/register` or `POST /api/v1/auth/login`.
2. Copy the returned `access_token`.
3. In Swagger UI, open the Authorize dialog if shown by the browser UI, or add
   this header in a manual API client:

```text
Authorization: Bearer <access_token>
```

4. Call `GET /api/v1/auth/me`, `GET /api/v1/users/me`, or a protected
   Products, Inventory, Sales Upload, Sales Transactions, Forecast Runs, ML
   Forecasting, Forecast Results, Reorder Recommendations, Dashboard
   Analytics, Reports, or Background Jobs endpoint.

## Current API Groups

- `Health`
- `auth`
- `Users`
- `Products`
- `Inventory`
- `Sales Upload`
- `Sales Transactions`
- `Forecast Runs`
- `ML Forecasting`
- `Forecast Results`
- `Reorder Recommendations`
- `Dashboard Analytics`
- `Reports`
- `Background Jobs`

## Auth APIs Implemented

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`

## Health APIs Available

- `GET /api/v1/health`
- `GET /api/v1/health/ready`

## User Profile APIs Implemented

- `GET /api/v1/users/me`
- `PATCH /api/v1/users/me`
- `POST /api/v1/users/me/change-password`

## Product Catalog APIs Implemented

- `POST /api/v1/products`
- `GET /api/v1/products`
- `GET /api/v1/products/{product_id}`
- `PATCH /api/v1/products/{product_id}`
- `DELETE /api/v1/products/{product_id}`

Product APIs require `Authorization: Bearer <access_token>`, return only the
current user's products, normalize SKUs, validate fixed units, support search,
filters, pagination, and safe sort fields, and use soft archive behavior.
Product records do not store stock quantities.

## Product Category APIs Implemented

- `POST /api/v1/products/categories`
- `GET /api/v1/products/categories`
- `PATCH /api/v1/products/categories/{category_id}`
- `DELETE /api/v1/products/categories/{category_id}`

Category names are unique per user after normalization. Category archive is
blocked while the category has active products.

## Product Units API Implemented

- `GET /api/v1/products/units`

Allowed units are `pcs`, `kg`, `gram`, `liter`, `ml`, `box`, `packet`, and
`dozen`.

## Inventory APIs Implemented

- `POST /api/v1/inventory/items`
- `GET /api/v1/inventory/items`
- `GET /api/v1/inventory/items/{product_id}`
- `PATCH /api/v1/inventory/items/{product_id}`
- `POST /api/v1/inventory/movements`
- `GET /api/v1/inventory/movements`
- `GET /api/v1/inventory/low-stock`
- `GET /api/v1/inventory/summary`

Inventory APIs require `Authorization: Bearer <access_token>`, validate product
ownership, return only the current user's inventory, and keep stock data inside
Inventory tables. `PATCH /inventory/items/{product_id}` updates thresholds and
active status only. Stock quantity changes must be recorded through
`POST /inventory/movements`, which creates immutable ledger rows.

## Sales Upload APIs Implemented

- `POST /api/v1/sales/uploads`
- `GET /api/v1/sales/uploads`
- `GET /api/v1/sales/uploads/{upload_id}`
- `GET /api/v1/sales/uploads/{upload_id}/rejected-rows`
- `GET /api/v1/sales/uploads/template`

Sales Upload APIs require `Authorization: Bearer <access_token>`. The upload
endpoint accepts multipart CSV files with required columns `sale_date`,
`product_sku`, and `quantity`. Optional columns are `unit_price`,
`total_amount`, `customer_name`, `channel`, and `notes`. Accepted rows are
stored as historical sales transactions for forecasting input. Rejected rows are
stored with safe row-level error messages. Sales upload does not reduce
Inventory stock.

## Sales Transactions APIs Implemented

- `POST /api/v1/sales/transactions`
- `GET /api/v1/sales/transactions`
- `GET /api/v1/sales/transactions/summary`
- `GET /api/v1/sales/transactions/trends`
- `GET /api/v1/sales/transactions/by-product`
- `GET /api/v1/sales/transactions/{transaction_id}`
- `PATCH /api/v1/sales/transactions/{transaction_id}`
- `DELETE /api/v1/sales/transactions/{transaction_id}`

Sales Upload ingests CSV files and creates clean rows. Sales Transactions
manages, queries, soft deletes, and aggregates those clean sales rows. Manual
transaction creation uses `source=manual`; CSV-created rows keep
`source=csv_upload`. Sales Transactions APIs require
`Authorization: Bearer <access_token>`, enforce product and transaction
ownership, exclude soft-deleted rows from default lists and aggregates, and do
not reduce Inventory stock.

## Forecast Run APIs Implemented

- `POST /api/v1/forecast-runs`
- `GET /api/v1/forecast-runs`
- `GET /api/v1/forecast-runs/options`
- `GET /api/v1/forecast-runs/{run_id}`
- `POST /api/v1/forecast-runs/{run_id}/process`
- `POST /api/v1/forecast-runs/{run_id}/cancel`

Forecast Run manages lifecycle metadata only: requested horizon, status,
timestamps, product/sales-data counts, and cancellation. ML Forecasting
processes pending or failed runs and writes predictions/metrics; Forecast Run
still does not expose dashboard-shaped result queries.

## ML Forecasting APIs Implemented

- `POST /api/v1/forecast-runs/{run_id}/process`
- `GET /api/v1/ml/forecasting/options`
- `GET /api/v1/ml/forecasting/health`

ML Forecasting APIs require `Authorization: Bearer <access_token>`. Processing
uses historical Sales Transactions as demand input, active Products as the
forecast target set, a deterministic Random Forest model when enough data is
available, and a recent-average fallback for sparse products. It persists
product-wise predictions and model metrics for the run. It does not reduce
Inventory stock and does not create reorder recommendations.

## Forecast Results APIs Implemented

- `GET /api/v1/forecast-results/runs/{run_id}`
- `GET /api/v1/forecast-results/runs/{run_id}/predictions`
- `GET /api/v1/forecast-results/runs/{run_id}/metrics`
- `GET /api/v1/forecast-results/runs/{run_id}/chart`
- `GET /api/v1/forecast-results/runs/{run_id}/products/{product_id}`

Forecast Results APIs require `Authorization: Bearer <access_token>`. They
expose persisted predictions and metrics created by ML Forecasting. They do not
generate predictions, update run status, reduce Inventory stock, or calculate
reorder recommendations. Prediction list/detail responses include product
metadata and optional inventory snapshot fields for context only.

Module boundaries:

- Forecast Runs: lifecycle metadata and cancellation.
- ML Forecasting: process pending/failed runs and persist predictions/metrics.
- Forecast Results: read/query persisted predictions and metrics.
- Reorder Recommendations: convert persisted forecast demand plus inventory
  snapshots into reorder decisions.

Manual verification flow:

1. Create products and historical Sales Transactions.
2. Create a forecast run with `POST /api/v1/forecast-runs`.
3. Process it with `POST /api/v1/forecast-runs/{run_id}/process`.
4. Read the results from `GET /api/v1/forecast-results/runs/{run_id}` and the
   related predictions, metrics, chart, and product-detail endpoints.

Chart actual-sales comparison uses matching Sales Transactions when they exist
for forecast dates. If no matching actual sales exist, `actual_quantity` is
returned as `null`.

## Reorder Recommendations APIs Implemented

- `POST /api/v1/recommendations/runs/{run_id}/generate`
- `GET /api/v1/recommendations`
- `GET /api/v1/recommendations/runs/{run_id}`
- `GET /api/v1/recommendations/runs/{run_id}/summary`
- `GET /api/v1/recommendations/{recommendation_id}`
- `PATCH /api/v1/recommendations/{recommendation_id}/status`

Reorder Recommendations APIs require `Authorization: Bearer <access_token>`.
Generation is allowed only for an owned completed forecast run with persisted
forecast predictions and inventory items for every forecasted product. The
module aggregates predicted demand by product, reads current stock, minimum
stock, and safety stock from Inventory, then stores deterministic reorder
decisions.

Formula:

```text
required_stock = predicted_demand + safety_stock
stock_gap = required_stock - current_stock
reorder_quantity = max(stock_gap, 0)
```

Risk levels are `critical`, `high`, `medium`, `low`, and `overstocked`.
Actions are `reorder_now`, `monitor`, `no_reorder_needed`, and
`overstock_review`. Recommendation status values are `open`, `acknowledged`,
and `dismissed`.

If recommendations already exist for a run, generation returns `409` unless the
request body includes `{"refresh": true}`. Refresh deletes and recreates only
recommendations for that same owned forecast run.

This module does not generate ML predictions, update forecast run status,
change inventory stock, create purchase orders, or expose dashboard-shaped
analytics APIs.

## Dashboard Analytics APIs Implemented

- `GET /api/v1/dashboard/summary`
- `GET /api/v1/dashboard/kpis`
- `GET /api/v1/dashboard/demand-trends`
- `GET /api/v1/dashboard/inventory-risk`
- `GET /api/v1/dashboard/forecast-overview`
- `GET /api/v1/dashboard/reorder-alerts`
- `GET /api/v1/dashboard/recent-activity`

Dashboard Analytics APIs require `Authorization: Bearer <access_token>`. They
combine read-only data from Products, Inventory, Sales Transactions, Sales
Uploads, Forecast Runs, Forecast Results, and Reorder Recommendations into
dashboard-ready summaries. They do not create products, mutate inventory,
upload sales, process forecasts, generate recommendations, or create reports.

`GET /dashboard/summary` returns the initial-load dashboard shape with KPIs,
demand trend preview, inventory risk, forecast overview, reorder alert preview,
and recent activity. If `date_from` or `date_to` is omitted, the service uses a
safe last-30-days range.

`GET /dashboard/demand-trends` supports `interval=day|week|month` plus optional
owned `product_id` and `category_id` filters. Soft-deleted sales transactions
are excluded.

`GET /dashboard/reorder-alerts` reads existing recommendation rows only. It can
filter by owned `forecast_run_id`, `risk_level`, `status`, and `limit`.

## Reports APIs Implemented

- `GET /api/v1/reports/model-performance`
- `GET /api/v1/reports/inventory-risk`
- `GET /api/v1/reports/reorder-summary`
- `GET /api/v1/reports/demand-forecast`
- `GET /api/v1/reports/sales-summary`
- `GET /api/v1/reports/options`

Reports APIs require `Authorization: Bearer <access_token>`. They provide
structured report-ready summaries for demo/viva workflows and optional CSV
exports using `format=csv`. Default output is JSON with `format=json`.

Report types:

- Model Performance Report: forecast runs plus model metrics.
- Inventory Risk Report: inventory stock-status counts and product rows.
- Reorder Summary Report: recommendation risk/status summaries.
- Demand Forecast Report: persisted forecast predictions for one owned
  `forecast_run_id`.
- Sales Summary Report: non-deleted Sales Transactions grouped by product.

Dashboard Analytics remains the live dashboard layer for cards and charts.
Reports is the export/reporting layer. Reports does not create products,
mutate inventory, upload sales, process forecasts, generate recommendations,
mutate dashboard data, or implement settings.

CSV exports return `text/csv` with a safe attachment filename and include only
the authenticated user's report rows. PDF and Excel exports are future scope.

## Background Jobs APIs Implemented

- `POST /api/v1/jobs/forecast-runs/{run_id}`
- `GET /api/v1/jobs`
- `GET /api/v1/jobs/health`
- `GET /api/v1/jobs/options`
- `GET /api/v1/jobs/{job_id}`
- `POST /api/v1/jobs/{job_id}/cancel`
- `POST /api/v1/jobs/{job_id}/retry`

Background Jobs APIs require `Authorization: Bearer <access_token>`. They move
forecast processing outside the FastAPI request lifecycle by enqueueing a
durable RQ job that calls the existing ML Forecasting service. The API does not
duplicate ML training, prediction generation, or reorder calculation logic.

Asynchronous flow:

1. Create a pending forecast run with `POST /api/v1/forecast-runs`.
2. Enqueue it with `POST /api/v1/jobs/forecast-runs/{run_id}`.
3. Poll `GET /api/v1/jobs/{job_id}` until the durable status is `finished` or
   `failed`.
4. Read Forecast Results after the forecast run is completed.

Only one active forecast-processing job can exist for the same forecast run.
Repeated enqueue requests return the existing active job. Queued jobs can be
cancelled safely; started jobs are not forcefully terminated and return a
conflict. Manual retry is supported for failed jobs until the configured retry
limit is reached.

`GET /api/v1/jobs/health` returns safe Redis/RQ queue counts and worker names.
It does not expose Redis credentials or internal stack traces.

## Pending Future Modules

- Settings

## Manual Browser Verification

Use Swagger UI at `/docs` to inspect request and response schemas. For protected
routes, register or login first, then pass the access token as a Bearer token.
Protected Auth, Users, Products, Inventory, Sales Upload, Sales Transactions,
Forecast Runs, ML Forecasting, Forecast Results, Reorder Recommendations,
Dashboard Analytics, Reports, and Background Jobs routes should be tested with
`Authorization: Bearer <access_token>`. Use the refresh token only with
`/auth/refresh` and `/auth/logout`; it should not be used as an access token.

Manual Reports checks:

```text
GET /api/v1/reports/options
GET /api/v1/reports/sales-summary?date_from=2026-07-01&date_to=2026-07-31
GET /api/v1/reports/sales-summary?format=csv
GET /api/v1/reports/demand-forecast?forecast_run_id=<run_id>
```

Manual Background Jobs checks:

```text
POST /api/v1/jobs/forecast-runs/<run_id>
GET /api/v1/jobs/<job_id>
GET /api/v1/jobs/health
GET /api/v1/jobs/options
```
