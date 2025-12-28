PR bundle for medium-priority test improvements

PR-01: Consolidate tenant helper under `tests.utils`

Title: tests: consolidate tenant helper under tests.utils
Branch: fix/tenant-utils

Description:
- Add `backend/tests/utils/tenants.py` that re-exports `create_tenant` from `tests/helpers/tenant.py`.
- Update `backend/tests/conftest.py` to prefer the new import path `tests.utils.tenants` when resolving the helper.

Rationale:
- Provides a stable import path for test helpers, simplifying imports and refactors.

Files included in patch: docs/patches/pr-01/backend_tests_utils_tenants.py, docs/patches/pr-01/conftest.py

---

PR-02: Add concurrency smoke test

Title: tests: add concurrency smoke test for tenant helper
Branch: test/tenant-concurrency

Description:
- Add `backend/tests/test_tenant_concurrency.py`, a lightweight threading-based smoke test that calls `create_tenant` concurrently.

Rationale:
- Surfaces race conditions in migrations or helper logic when tenants are created concurrently in CI.

Files included in patch: docs/patches/pr-02/backend_tests_test_tenant_concurrency.py

---

Apply instructions:
- See `docs/patches/pr-01/apply_instructions.txt` and `docs/patches/pr-02/apply_instructions.txt` for step-by-step commands to apply each patch and create the corresponding branch and commit.

Notes:
- I could push and open the PRs for you if you provide the remote repo URL or configure `origin` in this environment.
- Optionally I can run `snyk_code_scan` prior to opening PRs if you authenticate Snyk in this environment.
