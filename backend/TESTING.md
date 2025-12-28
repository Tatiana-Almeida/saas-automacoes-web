Testing notes

This project includes test-friendly fallbacks that are enabled only when
`saas_backend.settings_test` sets `TESTING = True`.

Why
- Some parts of the codebase rely on `django-tenants` and Postgres features
  (schemas, public tenant rows). To run unit tests quickly on local machines
  without Postgres, the code includes conservative, guarded fallbacks that
  are only active during tests.

What to know
- The `rbac` models will auto-assign a lightweight `Tenant` when `settings.TESTING`
  is true and no tenant is present. This avoids `NOT NULL` constraint failures
  in SQLite test runs.
- `EmailVerificationToken` creation logs were reduced to DEBUG to keep test output
  clean; token creation still raises on errors so tests fail loudly when issues
  happen.

How to run tests

Use the test settings (already configured in `saas_backend/settings_test.py`):

```powershell
# run full test suite
pytest -q
```

If you prefer to run tests against Postgres + django-tenants, set up a
Postgres instance and run with:

```powershell
$env:USE_DOCKER_POSTGRES = '1'
pytest -q
```

Notes
- These fallbacks are intentionally conservative and gated by `TESTING`.
  If you'd rather run tests only against Postgres, remove or revert the
  `TESTING`-gated behavior and run tests with a Postgres backend.
