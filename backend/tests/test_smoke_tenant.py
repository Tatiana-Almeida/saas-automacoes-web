import os

import pytest


def using_settings_test():
    return os.environ.get("DJANGO_SETTINGS_MODULE", "").endswith("settings_test")


@pytest.mark.skipif(using_settings_test(), reason="Needs Postgres/django-tenants")
def test_smoke_create_tenant(create_tenant, django_db_blocker):
    """Smoke test: create a tenant and verify its schema exists in Postgres."""
    # create_tenant fixture unblocks DB access
    tenant = create_tenant(schema_name="smoke_tenant", domain="smoke.localhost")
    assert tenant is not None

    # Verify schema exists at DB level
    with django_db_blocker.unblock():
        from django.db import connection

        with connection.cursor() as cur:
            cur.execute(
                "SELECT schema_name FROM information_schema.schemata WHERE schema_name=%s",
                ["smoke_tenant"],
            )
            row = cur.fetchone()
            assert row is not None
