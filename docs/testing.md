# Testing

The backend test suite is split into unit tests and integration-oriented smoke
tests. Tests set safe default environment variables in `app/tests/conftest.py`
so they do not depend on production configuration.

## Unit Tests

Unit tests currently cover configuration loading and app import behavior.

```powershell
python -m pytest app/tests/unit
```

## Integration Tests

Integration tests currently cover the health endpoints and an optional async
database session smoke test.

```powershell
python -m pytest app/tests/integration
```

The database session test checks whether the test database is reachable. If it
is not available, the test is skipped instead of failing.

## DB-Dependent Test Flow

Start local PostgreSQL:

```powershell
docker compose up -d postgres
```

Create the test database if needed:

```powershell
docker exec -it invora-postgres createdb -U postgres invora_test
```

Run tests:

```powershell
python -m pytest
```

## Future E2E Plan

Once business modules exist, add E2E tests for authenticated user journeys:
product creation, inventory updates, sales CSV upload, forecast run creation,
forecast result review, and reorder recommendation review.

## Coverage Expectations

Foundation tests should stay deterministic and fast. Future modules should add
focused unit tests for domain/application logic and integration tests for API
and database boundaries.
