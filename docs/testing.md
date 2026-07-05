# Testing

The backend test suite is split into unit tests and integration-oriented API
tests. Tests set safe environment variables in `app/tests/conftest.py` so they
do not depend on production configuration.

## Unit Tests

Unit tests cover:

- config loading and app import behavior
- password hashing and verification
- password policy validation
- access token creation and validation
- refresh token hashing
- duplicate email service behavior
- invalid login service behavior

```powershell
python -m pytest app/tests/unit
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

Auth API tests use a deterministic fake repository through FastAPI dependency
overrides. They do not touch production services.

```powershell
python -m pytest app/tests/integration
```

Run auth tests only:

```powershell
python -m pytest app/tests/unit/test_auth_passwords.py app/tests/unit/test_auth_tokens.py app/tests/unit/test_auth_service.py app/tests/integration/test_auth_api.py
```

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
python -m pytest
```

## Future E2E Plan

Once business modules exist, add E2E tests for authenticated user journeys:
profile updates, product creation, inventory updates, sales CSV upload,
forecast run creation, forecast result review, and reorder recommendation
review.

## Coverage Expectations

Foundation and Auth tests should stay deterministic and fast. Future modules
should add focused unit tests for domain/application logic and integration tests
for API and database boundaries.
