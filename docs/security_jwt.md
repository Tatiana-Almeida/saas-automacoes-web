# JWT Storage and Migration Recommendations

Context
-------
This project currently uses JWTs for authentication and in some places stores tokens in `localStorage` or `sessionStorage`. This exposes tokens to XSS risk: a malicious script can read tokens and hijack sessions.

Goals
-----
- Reduce risk of token theft via XSS
- Move towards more secure storage (HttpOnly cookies) while preserving developer ergonomics and backwards compatibility

Recommendations
---------------
1. Prefer HttpOnly, Secure cookies for access and refresh tokens.
   - Set `HttpOnly` to prevent JavaScript access.
   - Set `Secure` to require TLS.
   - Set `SameSite=Lax` or `Strict` depending on cross-site flows; `Lax` is a reasonable default for most apps.

2. Server-side changes (Django)
   - Return tokens in Set-Cookie headers rather than response bodies.
   - Create endpoints to rotate/refresh tokens using cookie values.
   - Implement CSRF protection for state-changing endpoints (Django's `CsrfViewMiddleware`). When using cookies, protect POST/PUT/PATCH/DELETE with CSRF tokens.

3. Client-side changes
   - Prefer sending requests with `fetch(..., credentials: 'include')` when using cookies.
   - Remove reliance on `localStorage` for persistent token storage; use an in-memory store only for transient values.

4. Transition strategy
   - Support both approaches during migration: if a request has Authorization: Bearer token, accept it; otherwise rely on cookie.
   - Introduce a short-lived compatibility mode and monitor for clients still using localStorage.

5. Trade-offs
   - Switching to cookies introduces CSRF risk: mitigate with CSRF tokens and SameSite policies.
   - Cookies are safer against XSS but require HTTPS and careful subdomain configuration.

Example (Django settings)
```
# In production settings
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False  # Django's CSRF cookie must be readable by JS to send header
CSRF_TRUSTED_ORIGINS = ["https://your-domain.com"]
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SAMESITE = "Lax"
```

Next steps
----------
- Implement cookie-based token endpoints in the backend.
- Add client-side changes to use credentials include and remove token reads from localStorage.
- Update README with migration plan and tests to verify CSRF protections.
