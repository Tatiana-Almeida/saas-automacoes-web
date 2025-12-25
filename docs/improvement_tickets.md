# Improvement Tickets

This document enumerates recommended improvement tickets generated during the test-stability diagnostic session. Each ticket includes a description, motivation, priority, and suggested implementation steps.

---

## TICKET-001: Ensure search_path on cursor for tenant migrations
- Priority: High
- Summary: Some DB adapters and connection pools do not honor higher-level `connection.set_schema()` calls for the underlying cursor used by Django management commands. Add an explicit `SET search_path TO <schema>` on the same DB cursor used to run migrations.
- Why: Prevents `MigrationSchemaMissing` when `migrate_schemas` creates `django_migrations` in tenant schema.
- Suggested files: `backend/tests/helpers/tenant.py`, `backend/tests/conftest.py`
- Notes: Already applied as test-only fixes; consider moving to production-safe utilities if needed.

## TICKET-002: Session-scoped tenant schema fixture
- Priority: Medium
- Summary: Add a `session`-scoped fixture that pre-creates and migrates commonly used tenant schemas once per test session to reduce flakiness and runtime overhead.
- Why: Reduces repeated migration runs across tests and simplifies concurrency issues.
- Suggested implementation: `backend/tests/conftest.py` add `ensure_tenant_schemas(session)` fixture that calls the existing helper with a lock.

## TICKET-003: Add diagnostic logging for schema/search_path during migrations
- Priority: Medium
- Summary: Add optional DEBUG logs printing `current_schema()` and `SHOW search_path` when running per-tenant migrations to aid future debugging in CI.
- Why: Helps triage intermittent MigrationSchemaMissing issues.

## TICKET-004: Integrate Snyk code scan in pre-PR steps
- Priority: Low
- Summary: Run `snyk_code_scan` on modified Python files before opening PRs for security checks, and fix any flagged issues.
- Why: Required by project security guidance.

## TICKET-005: Consolidate test helpers and document contract
- Priority: Low
- Summary: Move `create_tenant` to `tests/utils/tenants.py` (or similar) and document expected behavior (returns Tenant, sets `_skip_auto_migrate`, idempotency).

---

If you want I can create GitHub issues from these tickets (requires repo remote and API access) or generate individual PRs implementing the medium/low priority items.
