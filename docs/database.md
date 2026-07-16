# Database Operations

## Local PostgreSQL

Start only Invora's database service:

```powershell
docker compose up -d invora-postgres
docker compose exec invora-postgres sh -c 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

Run migrations with the same `.env` configuration as FastAPI:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m alembic current
.\.venv\Scripts\python.exe -m alembic check
```

`alembic/env.py` reads `DATABASE_URL` from `app.core.config`; the fallback URL
in `alembic.ini` is not used for application migrations.

## Hosted PostgreSQL

Set `DATABASE_URL` to the provider's host, database, credentials, and SSL
requirements using the `postgresql+asyncpg://` scheme. Keep the password in a
secret manager or untracked `.env`, never in source code.

```text
DATABASE_URL=postgresql+asyncpg://<username>:<password>@<host>/<database>?ssl=require
```

## VS Code Database Client

Install a PostgreSQL-capable VS Code extension such as Database Client JDBC.
Create a PostgreSQL connection using values from `.env` or your deployment
secret store:

| Setting | Local Docker | Hosted PostgreSQL |
| --- | --- | --- |
| Host | `localhost` | Provider host |
| Port | `POSTGRES_HOST_PORT` | Provider port |
| Database | `POSTGRES_DB` | Provider database |
| User | `POSTGRES_USER` | Provider user |
| Password | `POSTGRES_PASSWORD` | Provider secret |
| SSL | Disabled for local-only Docker | Provider-required SSL mode |

Do not paste a production connection URL or password into tracked VS Code
settings. For local Docker, confirm the service is healthy before connecting.
