try:
    # module import marker for test-time debug
    print("CORE_MIDDLEWARE_MODULE_LOADED")
except Exception:
    pass

# Test-time domain -> tenant registry. Tests may create Domain/Tenant rows
# inside transactions which are not visible to other DB connections used by
# tenant-detection middleware; registering the mapping here lets tests
# resolve tenants reliably without changing DB transaction semantics.
TEST_DOMAIN_REGISTRY = {}


def TenantMainMiddleware(get_response):
    """Wrapper around django_tenants' TenantMainMiddleware that first
    consults the in-process `TEST_DOMAIN_REGISTRY` to resolve tenants
    created inside pytest transactions. If a mapping exists for the
    request host, set `request.tenant` and the DB schema before
    delegating to the real middleware.
    """
    try:
        from django_tenants.middleware.main import (
            TenantMainMiddleware as RealTenantMainMiddleware,
        )
    except Exception:
        RealTenantMainMiddleware = None

    real = (
        RealTenantMainMiddleware(get_response)
        if RealTenantMainMiddleware is not None
        else None
    )

    def middleware(request):
        import logging
        logger = logging.getLogger("apps.core")

        # Diagnostic: record where host was resolved from for easier debugging
        host_source = None

        # Resolve host from multiple sources with clear priority:
        # 1. Explicit test registry mapping (fast in-process)
        # 2. HTTP header 'X_TENANT_HOST' (useful for tests/scripts)
        # 3. HTTP_HOST from META
        # 4. request.get_host() fallback
        host = None
        try:
            val = request.META.get("HTTP_X_TENANT_HOST") or request.META.get("X_TENANT_HOST")
            if val:
                host = val
                host_source = "header:X_TENANT_HOST"
        except Exception:
            host = None

        try:
            if not host:
                host = request.META.get("HTTP_HOST")
                if host:
                    host_source = host_source or "meta:HTTP_HOST"
        except Exception:
            pass

        try:
            if not host:
                host = request.get_host()
                if host:
                    host_source = host_source or "request:get_host"
        except Exception:
            pass

        # normalize host: strip port
        try:
            if host and ":" in host:
                host = host.split(":", 1)[0]
        except Exception:
            pass

        # Log resolved host info for observability
        try:
            logger.info("Tenant resolve: host=%s source=%s", host, host_source)
        except Exception:
            pass

        # Try test-domain registry first (fast, in-process)
        try:
            if host and host in TEST_DOMAIN_REGISTRY:
                t = TEST_DOMAIN_REGISTRY.get(host)
                request.tenant = t
                try:
                    from django.db import connection

                    connection.set_schema(t.schema_name)
                    logger.info("Set schema for test tenant %s", getattr(t, "schema_name", None))
                except Exception:
                    logger.exception(
                        "Failed to set schema for test tenant %s", getattr(t, "schema_name", None)
                    )
        except Exception:
            logger.exception(
                "Error while resolving tenant from TEST_DOMAIN_REGISTRY for host=%s", host
            )

        # If we resolved the tenant via TEST_DOMAIN_REGISTRY, skip the
        # django-tenants middleware to avoid its DB lookup which can't see
        # transaction-local Domain rows during pytest runs. Otherwise
        # delegate to the real middleware.
        try:
            if host and host in TEST_DOMAIN_REGISTRY:
                return get_response(request)
        except Exception:
            pass

        if real is not None:
            return real(request)
        return get_response(request)

    return middleware


def TenantContextMiddleware(get_response):
    def middleware(request):
        tenant = getattr(request, "tenant", None)
        if tenant is not None:
            try:
                request.tenant_id = tenant.id
                request.tenant_schema = getattr(tenant, "schema_name", None)
            except Exception:
                pass
        return get_response(request)

    return middleware


def EnforceActiveTenantMiddleware(get_response):
    from django.http import JsonResponse

    def middleware(request):
        tenant = getattr(request, "tenant", None)
        # If tenant has is_active and is False, block access
        try:
            if (
                tenant is not None
                and hasattr(tenant, "is_active")
                and tenant.is_active is False
            ):
                return JsonResponse({"detail": "Tenant suspenso"}, status=403)
        except Exception:
            # Fail open to avoid blocking due to edge errors
            pass
        return get_response(request)

    return middleware


def PlanLimitMiddleware(get_response):
    """Middleware para validar limites diários por plano antes de ações.
    Usa o atributo `throttle_scope` da view (ex.: send_whatsapp, email_send, etc.)
    e valida contra `settings.TENANT_PLAN_DAILY_LIMITS[plan][scope]` por tenant.
    Contadores são armazenados em cache até o fim do dia.
    """
    from django.conf import settings
    from django.http import JsonResponse
    from django.core.cache import cache
    from django.utils import timezone

    def _category_from_request(request):
        try:
            match = getattr(request, "resolver_match", None)
            func = getattr(match, "func", None)
            view_class = getattr(func, "view_class", None)
            scope = getattr(view_class, "throttle_scope", None)
            if scope:
                return scope
        except Exception:
            pass

        # If resolver_match wasn't set or had no scope, attempt to resolve the path now
        try:
            from django.urls import resolve

            r = resolve(getattr(request, "path", "/"))
            func = getattr(r, "func", None)
            view_class = getattr(func, "view_class", None)
            return getattr(view_class, "throttle_scope", None)
        except Exception:
            return None

    def _plan_code(tenant):
        try:
            # Preferência: referência de modelo Plan
            plan_obj = getattr(tenant, "plan_ref", None)
            code = getattr(plan_obj, "code", None)
            if code:
                return code
            # Fallback: campo string existente `plan`
            code = getattr(tenant, "plan", None)
            if code:
                return code
        except Exception:
            pass
        return None

    def _limit_for(tenant, plan_code, category):
        # Se houver plan_ref com daily_limits definidos, usar primeiro
        try:
            plan_obj = getattr(tenant, "plan_ref", None)
            daily_limits = getattr(plan_obj, "daily_limits", None)
            if isinstance(daily_limits, dict):
                val = daily_limits.get(category)
                if isinstance(val, int):
                    return val
        except Exception:
            pass
        # Fallback para settings
        limits = getattr(settings, "TENANT_PLAN_DAILY_LIMITS", {})
        return limits.get(plan_code, {}).get(category)

    def _cache_key(schema, category):
        today = timezone.now().date().isoformat()
        return f"plan_limit:{schema}:{category}:{today}"

    def _ttl_until_end_of_day():
        now = timezone.now()
        end = now.replace(hour=23, minute=59, second=59, microsecond=0)
        return int((end - now).total_seconds()) or 1

    def middleware(request):
        try:
            if request.method in ("POST", "PUT", "PATCH"):
                tenant = getattr(request, "tenant", None)
                schema = getattr(tenant, "schema_name", None)
                category = _category_from_request(request)
                plan_code = _plan_code(tenant)
                if tenant and schema and category and plan_code:
                    limit = _limit_for(tenant, plan_code, category)
                    if isinstance(limit, int) and limit >= 0:
                        key = _cache_key(schema, category)
                        try:
                            print(
                                f"PLAN_LIMIT check plan={plan_code} category={category} key={key}"
                            )
                        except Exception:
                            pass
                        count = cache.get(key, 0)
                        try:
                            print(f"PLAN_LIMIT count={count} limit={limit} for {key}")
                        except Exception:
                            pass
                        if count >= limit:
                            try:
                                print(
                                    f"PLAN_LIMIT blocked plan={plan_code} category={category} key={key} count={count} limit={limit}"
                                )
                            except Exception:
                                pass
                            return JsonResponse(
                                {
                                    "detail": "Limite diário do plano atingido",
                                    "plan": plan_code,
                                    "category": category,
                                    "limit": limit,
                                },
                                status=429,
                            )
                        # marcar para incrementar depois de sucesso
                        request._plan_limit_key = key
        except Exception:
            # Fail open para evitar bloquear em erro inesperado
            pass

        response = get_response(request)

        try:
            key = getattr(request, "_plan_limit_key", None)
            if (
                key
                and 200 <= getattr(response, "status_code", 500) < 300
                and request.method in ("POST", "PUT", "PATCH")
            ):
                ttl = _ttl_until_end_of_day()
                current = cache.get(key, 0)
                try:
                    print(f"PLAN_LIMIT increment key={key} current={current} ttl={ttl}")
                except Exception:
                    pass
                cache.set(key, int(current) + 1, timeout=ttl)
        except Exception:
            pass

        return response

    return middleware


def EnsureTenantSetMiddleware(get_response):
    """Fallback middleware to ensure `request.tenant` is set when the
    tenant-detection middleware did not populate it (useful for tests).
    This will attempt a domain lookup in the public schema and set the
    request.tenant and connection schema accordingly.
    """

    def middleware(request):
        try:
            if getattr(request, "tenant", None) is None:
                host = None
                try:
                    if hasattr(request, "META"):
                        host = request.META.get("HTTP_HOST")
                except Exception:
                    host = None
                # Fallback to `get_host()` which handles SERVER_NAME/PORT cases
                try:
                    if not host:
                        host = request.get_host()
                except Exception:
                    pass
                # Normalize host: strip optional port (e.g. 'example.com:8000' -> 'example.com')
                try:
                    if host and ":" in host:
                        host = host.split(":", 1)[0]
                except Exception:
                    pass
                try:
                    import logging

                    logger = logging.getLogger("apps.core")
                    logger.info("EnsureTenantSetMiddleware host lookup: %s", host)
                except Exception:
                    pass
                try:
                    # Print to stdout for pytest capture
                    print(f"ENSURE_TENANT host={host}")
                except Exception:
                    pass
                try:
                    from django.db import connection

                    connection.set_schema_to_public()
                except Exception:
                    pass
                try:
                    from apps.tenants.models import Domain, Tenant

                    # Test registry shortcut: prefer in-memory mapping when present
                    t = None
                    _reg = TEST_DOMAIN_REGISTRY
                    if host and host in _reg:
                        t = _reg.get(host)
                        try:
                            print(
                                f"ENSURE_TENANT registry hit host={host} tenant={getattr(t,'schema_name',None)}"
                            )
                        except Exception:
                            pass
                    else:
                        d = Domain.objects.filter(domain=host).first()
                        if d:
                            t = Tenant.objects.filter(id=d.tenant_id).first()

                    try:
                        import logging

                        logging.getLogger("apps.core").info(
                            "EnsureTenantSetMiddleware found Domain=%s Tenant=%s",
                            getattr(d, "domain", None) if "d" in locals() else None,
                            getattr(t, "schema_name", None),
                        )
                    except Exception:
                        pass

                    try:
                        if t and host in _reg:
                            print(
                                f"ENSURE_TENANT set from registry host={host} tenant={getattr(t,'schema_name',None)}"
                            )
                    except Exception:
                        pass

                    try:
                        print(
                            f"ENSURE_TENANT found Domain={getattr(d,'domain',None) if 'd' in locals() else None} Tenant={getattr(t,'schema_name',None)}"
                        )
                    except Exception:
                        pass

                    if t:
                        request.tenant = t
                        try:
                            connection.set_schema(t.schema_name)
                        except Exception:
                            pass
                        try:
                            import logging

                            logging.getLogger("apps.core").info(
                                "EnsureTenantSetMiddleware set request.tenant=%s",
                                getattr(request.tenant, "schema_name", None),
                            )
                        except Exception:
                            pass
                        try:
                            print(
                                f"ENSURE_TENANT set request.tenant={getattr(request.tenant,'schema_name',None)}"
                            )
                        except Exception:
                            pass
                except Exception:
                    pass
        except Exception:
            pass
        return get_response(request)

    return middleware


def RequestDebugMiddleware(get_response):
    """Lightweight middleware to log host, resolved host, tenant and schema for debugging tests."""

    def middleware(request):
        response = None
        try:
            import logging

            logger = logging.getLogger("apps.core")
            host = None
            try:
                host = request.META.get("HTTP_HOST")
            except Exception:
                host = None
            try:
                resolved = request.get_host()
            except Exception:
                resolved = None
            tenant = getattr(request, "tenant", None)
            try:
                from django.db import connection

                schema = getattr(connection, "schema_name", None)
            except Exception:
                schema = None
            # Log pre-dispatch routing info
            logger.info(
                "RequestDebugMiddleware PRE host=%s resolved=%s tenant=%s schema=%s path=%s",
                host,
                resolved,
                getattr(tenant, "schema_name", None) if tenant else None,
                schema,
                getattr(request, "path", None),
            )
            try:
                # Also print to stdout so pytest captures immediately
                print(
                    f"DBG PRE host={host} resolved={resolved} tenant={getattr(tenant, 'schema_name', None) if tenant else None} schema={schema} path={getattr(request, 'path', None)}"
                )
            except Exception:
                pass

            # Log selected META keys to inspect what the test client sends
            try:
                meta_snapshot = {
                    k: request.META.get(k)
                    for k in (
                        "HTTP_HOST",
                        "SERVER_NAME",
                        "SERVER_PORT",
                        "PATH_INFO",
                        "REMOTE_ADDR",
                    )
                }
                logger.info("RequestDebugMiddleware PRE META: %s", meta_snapshot)
            except Exception:
                pass

            # Log URL resolver summary before dispatch
            try:
                from django.urls import get_resolver

                resolver = get_resolver()
                urlconf_name = getattr(resolver, "urlconf_name", None)
                patterns = getattr(resolver, "url_patterns", None)
                logger.info(
                    "RequestDebugMiddleware PRE resolver urlconf=%s root_patterns=%s",
                    urlconf_name,
                    len(patterns) if patterns is not None else None,
                )
            except Exception:
                pass
        except Exception:
            pass

        # Dispatch request to next middleware/view
        try:
            response = get_response(request)
        finally:
            try:
                import logging

                logger = logging.getLogger("apps.core")
                # Log post-dispatch resolver_match and response status
                try:
                    rm = getattr(request, "resolver_match", None)
                    rm_name = None
                    if rm is not None:
                        rm_name = (
                            getattr(rm, "view_name", None)
                            or getattr(rm, "url_name", None)
                            or str(rm)
                        )
                except Exception:
                    rm_name = None
                try:
                    from django.db import connection

                    schema = getattr(connection, "schema_name", None)
                except Exception:
                    schema = None
                logger.info(
                    "RequestDebugMiddleware POST resolver_match=%s tenant=%s schema=%s response_status=%s",
                    rm_name,
                    getattr(getattr(request, "tenant", None), "schema_name", None),
                    schema,
                    getattr(response, "status_code", None),
                )
                try:
                    # Extra: attempt to resolve the path and print result or exception
                    from django.urls import resolve

                    try:
                        r = resolve(getattr(request, "path", "/"))
                        print(
                            f"DBG RESOLVE path={getattr(request,'path',None)} -> func={r.func} view_name={getattr(r,'view_name',None)} url_name={getattr(r,'url_name',None)}"
                        )
                    except Exception as e:
                        print(
                            f"DBG RESOLVE FAILED path={getattr(request,'path',None)} error={e}"
                        )
                except Exception:
                    pass
            except Exception:
                pass

        return response

    return middleware


def InitialRequestDebugMiddleware(get_response):
    """Runs first to capture the raw request META and whether a tenant
    attribute is present before any tenant middleware mutates the request."""

    def middleware(request):
        try:
            host = None
            try:
                host = request.META.get("HTTP_HOST")
            except Exception:
                host = None
            try:
                print(
                    f"INITIAL_REQ host={host} tenant_present={hasattr(request, 'tenant')} path={getattr(request,'path',None)}"
                )
            except Exception:
                pass
        except Exception:
            pass
        return get_response(request)

    return middleware
