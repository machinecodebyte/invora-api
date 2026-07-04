# Project Runner

Follow these steps from the `backend/` directory.

## 1. Create the Environment File

```powershell
Copy-Item .env.example .env
```

Review `.env` and keep secrets out of source control. The default
`DATABASE_URL` expects PostgreSQL on `localhost:5432`.

## 2. Install Dependencies

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

## 3. Start Local Services

```powershell
docker compose up -d postgres redis
```

Check service health:

```powershell
docker compose ps
```

## 4. Run Migrations

```powershell
alembic upgrade head
alembic current
```

The current baseline migration does not create business tables.

## 5. Start FastAPI

```powershell
uvicorn app.main:app --reload
```

API root:

```text
http://127.0.0.1:8000
```

OpenAPI docs:

```text
http://127.0.0.1:8000/docs
```

## 6. Verify Health APIs

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health/ready
```

`/health` checks application availability. `/health/ready` also checks database
connectivity and returns a safe `503` response if PostgreSQL is unavailable.
