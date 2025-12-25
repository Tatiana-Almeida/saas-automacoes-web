# PR: Add concurrency smoke test for tenant helper

Summary
- Add a lightweight concurrency smoke test `backend/tests/test_tenant_concurrency.py`.

What changed
- New test that spawns a few threads calling the `create_tenant` helper concurrently.

Why
- Surfaces races or failures when multiple test processes/threads create/migrate tenant schemas concurrently.

Notes
- This test is intentionally lightweight and will be skipped/ignored under SQLite/lightweight test settings.
