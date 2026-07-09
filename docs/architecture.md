# Architecture

The backend is a modular monolith. It deploys as one FastAPI service while each
business area keeps its code in a clear module boundary.

## Layers

Each business module should follow this shape:

```text
api/
application/
domain/
infrastructure/
```

## API Layer

The API layer owns FastAPI routers, request schemas, response schemas, HTTP
status choices, and dependency wiring.

## Application Layer

The application layer coordinates use cases. It should orchestrate domain
objects, repositories, transactions, and external services without containing
HTTP-specific logic.

## Domain Layer

The domain layer owns business rules, entities, value objects, domain services,
and business exceptions. It should not depend on FastAPI or SQLAlchemy sessions.

## Infrastructure Layer

The infrastructure layer owns database repositories, external integrations,
message/job adapters, and persistence details.

## Shared Folder Rules

`app/shared` is for small cross-module utilities such as response envelopes,
pagination primitives, enums, and dependency re-exports. It should not become a
place for business logic.

## Foundation Boundaries

The current backend includes foundation, auth, user profile, products,
inventory, sales upload, sales transactions, forecast run, ML forecasting,
forecast results, and reorder recommendations modules. Dashboard analytics,
reports, jobs, and settings remain pending.
