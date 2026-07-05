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
   Products endpoint.

## Current API Groups

- `Health`
- `auth`
- `Users`
- `Products`

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

## Pending Future Modules

- Inventory
- Sales Upload
- Forecasting
- Recommendations
- Dashboard
- Reports
- Settings

## Manual Browser Verification

Use Swagger UI at `/docs` to inspect request and response schemas. For protected
routes, register or login first, then pass the access token as a Bearer token.
Protected Auth, Users, and Products routes should be tested with
`Authorization: Bearer <access_token>`. Use the refresh token only with
`/auth/refresh` and `/auth/logout`; it should not be used as an access token.
