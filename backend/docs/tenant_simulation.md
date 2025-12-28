Tenant simulation and frontend notes
====================================

The backend supports tenant resolution using the request host and via an explicit
header `X-Tenant-Host` (Django reads this as `HTTP_X_TENANT_HOST`). This is useful
for local development and tests where creating DNS entries or Postgres schemas
may be inconvenient. The frontend helper `api.ts` already attaches this header
when a tenant host is configured in the UI.

Examples:

- Set tenant host in your browser devtools (or `sessionStorage`) and the frontend
  will include the header with API requests.
- Use the Django test client passing `HTTP_X_TENANT_HOST` or `HTTP_HOST` in the
  request kwargs to simulate tenant-scoped requests in tests.

Frontend files of interest:

- `frontend/src/api.ts` — attaches `X-TENANT-HOST` header from app state.
- `frontend/src/AuthContext.tsx` — stores tenant selection in sessionStorage.

Test helpers:

- `tests.helpers.tenant.create_tenant` — robust test helper that creates tenant
  rows and runs `migrate_schemas` where applicable.
- `apps.tenants.helpers.create_tenant` — runtime helper safe for `settings.TESTING`.
