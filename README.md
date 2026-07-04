# AI-Based Demand Forecasting and Inventory Reorder Recommendation System

This repository currently contains the backend foundation for a modular monolith
FastAPI application. It is prepared for future modules such as auth, products,
inventory, sales upload, forecasting, recommendations, dashboard analytics, and
reports.

## Current Scope

Implemented now:

- FastAPI application setup with API v1 routing
- Pydantic Settings configuration
- Structured JSON request logging
- Global exception handlers
- Health and readiness APIs
- Async SQLAlchemy 2.x session setup for PostgreSQL
- Alembic async migration setup
- Docker Compose services for PostgreSQL and Redis
- Pytest and Ruff setup
- Documentation for local running, testing, architecture, and commands

Business features are intentionally not implemented yet.

## Tech Stack

- Python 3.11+
- FastAPI
- Pydantic v2 and Pydantic Settings
- SQLAlchemy 2.x async
- PostgreSQL with asyncpg
- Alembic
- Redis configuration placeholder
- Pytest, pytest-asyncio, httpx
- Ruff
- Docker Compose

## Quick Start

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
docker compose up -d postgres redis
alembic upgrade head
uvicorn app.main:app --reload
```

Verify:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health/ready
```

## Documentation

- [Docs overview](docs/README.md)
- [Run the project](docs/project-runner.md)
- [Commands](docs/commands.md)
- [Testing](docs/testing.md)
- [Architecture](docs/architecture.md)
- [Progress](docs/progress.md)

## Next Recommended Module

Build the Auth Module next, followed by the Users/Profile module. Auth should
establish identity, password handling, token creation, and protected route
patterns before product or inventory features depend on user context.
