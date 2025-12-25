# PR: Consolidate tenant test helper under `tests.utils`

Summary
- Move/Expose the tenant creation helper under a stable import path: `tests.utils.tenants.create_tenant`.

What changed
- Added `backend/tests/utils/tenants.py` that re-exports `create_tenant` from `tests/helpers/tenant.py`.
- Updated `backend/tests/conftest.py` to prefer the new import path when resolving the helper.

Why
- Tests should import helpers from a stable, documented path; this avoids fragile relative imports and simplifies downstream refactors.

Notes
- No behavior changes; this is a refactor and import-path consolidation.
