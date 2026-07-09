# Testing

The backend test suite is split into unit tests and integration-oriented API
tests. Tests set safe environment variables in `app/tests/conftest.py` so they
do not depend on production configuration.

Use `python3 -m ...` on Unix/macOS/Linux. On Windows, use `py -3 -m ...`
when the `python` command is unavailable. Docker-only runs can use
`docker compose exec backend python -m pytest`.

## Unit Tests

Unit tests cover:

- config loading and app import behavior
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

Auth and User Profile API tests use a deterministic fake repository through
FastAPI dependency overrides. Product, Inventory, Sales Upload, Sales
Transactions, Forecast Run, ML Forecasting, and Forecast Results API tests use
deterministic fake repositories through the same override pattern. They do not
touch production services.

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

Protected route tests register a user through the Auth API, use the returned
Bearer access token for Users, Products, Inventory, Sales Upload, and Sales
Transactions, Forecast Run, ML Forecasting, and Forecast Results routes, and
reuse fake repositories to verify profile, password, catalog, inventory, sales
upload, sales transaction, forecast run, ML processing, and forecast result
query behavior.

## DB-Dependent Test Flow

The async database session smoke test checks whether the test database is
reachable. If it is not available, the test is skipped instead of failing.

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
Transactions, Forecast Run, ML Forecasting, and Forecast Results.

## Future E2E Plan

Once business modules exist, add E2E tests for authenticated user journeys:
inventory updates, sales CSV upload, sales transaction review, forecast run
creation, forecast result review, and reorder recommendation review.

## Coverage Expectations

Foundation and Auth tests should stay deterministic and fast. Future modules
should add focused unit tests for domain/application logic and integration tests
for API and database boundaries.
