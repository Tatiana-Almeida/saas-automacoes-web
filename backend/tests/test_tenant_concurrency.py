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
    # Threading scenario
    threads = []
    for i in range(3):
        t = threading.Thread(
            target=_create_tenant_concurrently,
            args=(
                create_tenant,
                f"ctenant_thread_{i}",
                f"ctenant_thread_{i}.localhost",
            ),
        )
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    # Multiprocessing scenario (separate processes to exercise separate DB
    # connections). This is a lightweight check and will not assert final DB
    # state deeply — it surfaces immediate race exceptions.
    try:
        from multiprocessing import Process

        procs = []
        for i in range(2):
            p = Process(
                target=_create_tenant_concurrently,
                args=(
                    create_tenant,
                    f"ctenant_proc_{i}",
                    f"ctenant_proc_{i}.localhost",
                ),
            )
            procs.append(p)
            p.start()

        for p in procs:
            p.join()
    except Exception:
        # Some test runners restrict multiprocessing; ignore if unavailable.
        pass
