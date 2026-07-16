# Testing

The backend test suite is split into unit tests and integration-oriented API
tests. Tests set safe environment variables in `app/tests/conftest.py` so they
do not depend on production configuration.

Use `python3 -m ...` on Unix/macOS/Linux. On Windows, create `.venv` with
`py -3 -m venv .venv`, then use `.\.venv\Scripts\python.exe -m ...`.
Docker-only runs can use
`docker compose exec backend python -m pytest`.

## Unit Tests

Unit tests cover:

- config loading and app import behavior
- database URL normalization, production debug protection, and local server
  port fallback behavior
- credentialed-CORS wildcard rejection and duplicate API-route detection
- password hashing and verification
- password policy validation
- access token creation and validation
- refresh token hashing
- duplicate email service behavior
- invalid login service behavior
- user profile update validation
- current password verification
- password hash update behavior
- product SKU normalization
- product category name normalization
- product unit and price validation
- duplicate product SKU and duplicate category behavior
- category archive conflict with active products
- product sort field validation
- inventory stock-in, stock-out, and adjustment calculations
- inventory negative stock prevention
- inventory low-stock and out-of-stock status calculations
- inventory threshold, movement type, and sort field validation
- sales upload required-column validation
- sales upload SKU/date/quantity/price validation
- sales upload total amount calculation
- sales upload status and safe filename handling
- sales upload row rejection reasons
- sales transaction date, quantity, price, amount, source, date range, and sort
  validation
- sales transaction protected field rejection and update amount recalculation
- forecast run horizon, lifecycle, cancellation, date range, sort/order, and
  minimum data validation
- ML forecasting preprocessing, daily aggregation, missing-date filling,
  feature generation, lag/rolling features, metric calculation, zero-safe MAPE,
  deterministic prediction output, sparse-history fallback, and negative-demand
  clipping
- forecast result readiness, date range, interval, sort, and product-detail
  result validation
- reorder recommendation formula, risk/action rules, regeneration policy,
  filter validation, sort validation, date range validation, and status
  transition validation
- dashboard analytics date range, interval, limit, risk-level, and
  recommendation-status validation
- reports date range, export format, risk/status/stock-status filter, safe CSV
  filename, CSV serialization validation, and spreadsheet formula escaping
- background job status transitions, cancellation rules, retry rules, retry
  limits, RQ status mapping, safe sort validation, result summary
  sanitization, retryable exception classification, worker success behavior,
  worker failure behavior, and deterministic RQ SimpleWorker execution
- system settings defaults, all supported values and bounds, stock precision,
  timezone/locale validation, protected/unknown field rejection, metadata
  safety, category reset, full reset, and concurrent first-read behavior

```powershell
python3 -m pytest app/tests/unit
```

## Integration Tests

Integration tests cover:

- health endpoints
- register success
- duplicate register returning `409`
- login success
- invalid password returning `401`
- `/me` without token returning `401`
- `/me` with a valid token returning the user
- refresh-token rotation
- logout revocation
- revoked refresh token reuse rejection
- user profile protected route behavior
- allowed profile updates
- protected profile-field rejection
- password change with old/new login behavior
- refresh-token revocation after password change
- product protected route behavior
- product create/list/get/update/archive behavior
- duplicate SKU rejection per user
- same SKU allowed for different users
- user-scoped product access
- product search/filter/pagination
- product category create/list/update/archive conflict behavior
- product units API behavior
- inventory protected route behavior
- inventory item create/list/get/update behavior
- duplicate inventory item rejection
- product ownership enforcement for inventory
- stock movements updating balances through the ledger
- insufficient stock rejection
- low-stock endpoint behavior
- inventory summary counts
- sales upload protected route behavior
- sales CSV upload success and missing-column rejection
- mixed valid/invalid sales row persistence
- unknown SKU row rejection
- user-scoped sales upload access
- rejected rows listing
- sales upload template behavior
- sales upload does not reduce inventory stock
- sales transaction protected route behavior
- manual sales transaction create/list/detail/update/soft-delete behavior
- sales transaction ownership enforcement
- sales transaction product, date range, and source filters
- sales transaction summary, trends, and by-product aggregates
- CSV-upload-created rows appearing in Sales Transactions queries
- sales transaction create does not reduce inventory stock
- forecast run protected route behavior
- forecast run create/list/detail/cancel/options behavior
- forecast run ownership enforcement
- forecast run product and sales-data pre-flight validation
- ML forecast run processing auth, ownership, status guards, clean missing-data
  failures, persisted predictions, persisted metrics, options, and health
- forecast result overview, not-ready conflict, ownership, paginated
  predictions, product/date/search filters, metrics, chart data with actual
  sales comparison, product detail, and safe missing-run handling
- reorder recommendation generation auth, completed-run guard, missing
  prediction guard, missing inventory guard, refresh behavior, user scoping,
  listing, run summary, detail, and acknowledge/dismiss status behavior
- dashboard analytics auth, empty-state summary, KPI scoping, demand trend
  aggregation and filters, inventory risk previews, forecast overview,
  reorder alert filters, and recent activity feed behavior
- reports auth, model performance empty/scoped reports, inventory risk counts,
  reorder summary counts, demand forecast run ownership, sales summary
  aggregation, options metadata, CSV export, invalid format, and invalid date
  range behavior
- background jobs auth, forecast-run enqueue, durable job creation, RQ job id
  persistence, duplicate active enqueue idempotency, forecast-run ownership,
  non-processable run rejection, user-scoped job listing/detail, queued
  cancellation, failed-job retry, retry limit enforcement, queue unavailable
  `503`, queue health, and options behavior
- system settings auth, first-read default creation, no-secret response shape,
  full and category updates, protected/unknown field rejection, all reset,
  category reset, user scoping, options, category validation, and concurrent
  first reads

Auth and User Profile API tests use a deterministic fake repository through
FastAPI dependency overrides. Product, Inventory, Sales Upload, Sales
Transactions, Forecast Run, ML Forecasting, and Forecast Results API tests use
deterministic fake repositories through the same override pattern. Reorder
Recommendation API tests use the same fake auth/product/inventory/forecast
repositories plus a fake recommendation repository. Dashboard Analytics API
tests use a fake dashboard repository that reads from the same fake module
stores. Reports API tests use a fake reports repository that reads the same
fake module stores. Background Jobs API tests use a fake durable job repository
and fake dispatcher so API behavior stays deterministic and never touches
production Redis. They do not touch production services. System Settings API
tests use a deterministic user-scoped settings repository; the production
repository uses PostgreSQL `INSERT ... ON CONFLICT DO NOTHING` to preserve the
same one-row-per-user guarantee under concurrent first reads.

```powershell
python3 -m pytest app/tests/integration
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

Run background jobs tests only:

```powershell
python3 -m pytest app/tests/unit/test_jobs.py app/tests/integration/test_jobs_api.py
```

Run System Settings tests only:

```powershell
python3 -m pytest app/tests/unit/test_settings.py app/tests/integration/test_settings_api.py
py -3 -m pytest app/tests/unit/test_settings.py app/tests/integration/test_settings_api.py
docker compose exec backend python -m pytest app/tests/unit/test_settings.py app/tests/integration/test_settings_api.py
```

Run the RQ worker-boundary test only:

```powershell
python3 -m pytest app/tests/unit/test_jobs.py -k rq
```

Protected route tests register a user through the Auth API, use the returned
Bearer access token for Users, Products, Inventory, Sales Upload, and Sales
Transactions, Forecast Run, ML Forecasting, Forecast Results, and Reorder
Recommendations, Dashboard Analytics, Reports, and Background Jobs routes, and reuse fake
repositories to verify profile, password, catalog, inventory, sales upload,
sales transaction, forecast run, ML processing, forecast result query behavior,
recommendation generation, dashboard aggregation, report generation, job
enqueueing, job cancellation, and job retry behavior.

## DB-Dependent Test Flow

The async database session smoke test checks whether the test database is
reachable. If it is not available, the test is skipped instead of failing.

Run `python3 -m alembic check` against a reachable PostgreSQL database to
ensure ORM metadata matches the migration-created schema.

Start local PostgreSQL:

```powershell
docker compose up -d invora-postgres
```

Create the test database if needed:

```powershell
docker exec -it invora-postgres createdb -U postgres invora_test
```

Run tests:

```powershell
python3 -m pytest
```

Docker-only test run:

```powershell
docker compose exec backend python -m pytest
```

The completed-module regression suite currently covers Foundation, Auth &
Identity, User Profile, Product Catalog, Inventory, Sales Upload, Sales
Transactions, Forecast Run, ML Forecasting, Forecast Results, Reorder
Recommendations, Dashboard Analytics, Reports, Background Jobs, and System
Settings.
Background Jobs tests add RQ queue/worker behavior without requiring a
permanently running worker process. System Settings tests run without a live
database or Redis dependency; the database migration is checked separately.

## Future E2E Plan

Once business modules exist, add E2E tests for authenticated user journeys:
inventory updates, sales CSV upload, sales transaction review, forecast run
creation, forecast result review, reorder recommendation review, and dashboard
analytics/reporting review.

## Coverage Expectations

Foundation and Auth tests should stay deterministic and fast. Future modules
should add focused unit tests for domain/application logic and integration tests
for API and database boundaries.
