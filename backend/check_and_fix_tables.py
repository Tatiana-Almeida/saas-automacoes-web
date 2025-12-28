import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "saas_backend.settings")
django.setup()

from django.db import connection
from django_tenants.utils import schema_context

with schema_context("public"):
    cursor = connection.cursor()
    cursor.execute(
        "SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename LIKE 'token_blacklist%'"
    )
    tables = [r[0] for r in cursor.fetchall()]

    if not tables:
        from django.core.management import call_command

        call_command("migrate", "token_blacklist", "--database", "default")
