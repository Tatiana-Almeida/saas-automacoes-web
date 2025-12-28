import threading


def _create_tenant_concurrently(create_tenant, schema_name, domain):
    # Lightweight wrapper used by threads; uses the test fixture helper.
    create_tenant(schema_name=schema_name, domain=domain)


def test_create_tenants_concurrently(create_tenant):
    """Basic concurrency smoke test to ensure helper tolerates parallel calls.

    This is a lightweight test that runs the helper multiple times in
    separate threads; it does not assert deep DB state but will surface
    immediate migration/lock races as exceptions.
    """
    threads = []
    for i in range(3):
        t = threading.Thread(
            target=_create_tenant_concurrently,
            args=(create_tenant, f"ctenant_{i}", f"ctenant_{i}.localhost"),
        )
        threads.append(t)
        t.start()

    for t in threads:
        t.join()
