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
   Products, Inventory, Sales Upload, or Sales Transactions endpoint.

## Current API Groups

- `Health`
- `auth`
- `Users`
- `Products`
- `Inventory`
- `Sales Upload`
- `Sales Transactions`

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

## Pending Future Modules

- Forecasting
- Recommendations
- Dashboard
- Reports
- Settings

## Manual Browser Verification

Use Swagger UI at `/docs` to inspect request and response schemas. For protected
routes, register or login first, then pass the access token as a Bearer token.
Protected Auth, Users, Products, Inventory, Sales Upload, and Sales
Transactions routes should be tested with
`Authorization: Bearer <access_token>`. Use the refresh token only with
`/auth/refresh` and `/auth/logout`; it should not be used as an access token.
