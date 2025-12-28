## Testing guide and helper contracts

This document explains testing helpers, fixtures and recommended patterns
for writing tests that interact with `django-tenants` multi-tenant schemas.

Key helpers
- `tests.helpers.tenant.create_tenant(schema_name, domain, ...)` — creates
  a `Tenant` model instance, ensures the DB schema exists, applies tenant
  migrations and registers the domain in the in-process registry. The
  helper marks the created instance with `_skip_auto_migrate` to avoid
  duplicate scheduled migrations.
- `tests.utils.tenants.create_tenant` — stable re-export of the helper.
- `tests.utils.db_lock.advisory_lock(schema_name)` — context manager that
  acquires a Postgres advisory lock for a given schema name (best-effort
  no-op on non-Postgres).

Fixtures
- `create_tenant` — fixture returning the `create_tenant` helper.
- `ensure_tenant_schemas` — session-scoped fixture (opt-in) that pre-creates
  a set of common tenant schemas to speed tests and reduce migration races.

Recommended test patterns
- Use `transactional_db` (provided automatically by `conftest.py`) when tests
  call `create_tenant()` since schema creation and migrations need an
  unblocked DB connection.
- Prefer `tests.utils.tenants.create_tenant` as the import path to avoid
  fragile relative imports.
- For concurrent scenarios, use the provided concurrency smoke test as a
  reference; consider isolating long-running concurrency tests behind
  markers so they can be run separately.

Local run
- Use `scripts/test-local.sh` to run the backend container and execute tests
  inside the `backend-dev` container (recommended to reproduce CI behavior).
