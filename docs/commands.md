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

## Docker Compose

```powershell
docker compose up -d postgres redis
docker compose ps
docker compose logs postgres
docker compose logs redis
docker compose down
```

Reset local service containers and volumes:

```powershell
docker compose down -v
docker compose up -d postgres redis
```

## Run Server

```powershell
uvicorn app.main:app --reload
```

## Alembic

```powershell
alembic current
alembic upgrade head
alembic revision --autogenerate -m "describe change"
alembic downgrade -1
```

## Tests

```powershell
python -m pytest
```

Run one test file:

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
