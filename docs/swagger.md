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

4. Call `GET /api/v1/auth/me` or `GET /api/v1/users/me`.

## Current API Groups

- `auth`
- `Users`
- `health`

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

## Pending Future Modules

- Products
- Inventory
- Sales Upload and Sales Transactions
- Forecasting
- Recommendations
- Dashboard
- Reports
- Background Jobs
- Settings

## Manual Browser Verification

Use Swagger UI at `/docs` to inspect request and response schemas. For protected
routes, register or login first, then pass the access token as a Bearer token.
Protected Auth and Users routes should be tested with `Authorization: Bearer
<access_token>`. Use the refresh token only with `/auth/refresh` and
`/auth/logout`; it should not be used as an access token.
