# SaaS Frontend (Vite + React + TS)

Dev server: Vite on http://localhost:5173
API base: `VITE_API_URL` (default: http://localhost:8080)
Auth: JWT Access stored in `localStorage` (`access_token`)
Routing: react-router-dom (login public; dashboard/users protected)

## Quickstart

```powershell
cd frontend
npm i
npm run dev
```

Open http://localhost:5173

Optionally set API base:
```powershell
$env:VITE_API_URL = "http://localhost:8080"
npm run dev
```

## Structure
- `src/services/api.ts`: axios instance with Authorization header from `localStorage`
- `src/services/auth.ts`: login/logout helpers
- `src/context/AuthContext.tsx`: loads `/api/v1/users/me` when authenticated
- `src/pages/Login.tsx`: login form POST `/api/v1/auth/token`
- `src/pages/Dashboard.tsx`: placeholder
- `src/pages/Users.tsx`: placeholder fetching current user

## Multi-tenant local testing
If you need to target a specific tenant domain in dev, you can set a temporary header:
```js
sessionStorage.setItem('tenant_host', 'acme.localhost')
```
The axios client will add `Host: acme.localhost` in requests (useful against the Dockerized backend mapping tenants by host).

## Build
```powershell
npm run build
npm run preview
```

## Notes
- Backend envelope for success `{ success, message, data }` is unwrapped in pages.
- For refresh tokens or cookie-based auth, extend `api.ts` interceptors accordingly.
