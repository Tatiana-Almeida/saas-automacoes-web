from contextlib import contextmanager

from django.db import connection


@contextmanager
def advisory_lock(schema_name: str):
    """Acquire a Postgres advisory lock for a given schema name.

    Uses `hashtext` to map a text key to an integer. If advisory locks are not
    available or the DB is not Postgres, this is a no-op (fails silently).
    """
    try:
        with connection.cursor() as cursor:
            try:
                cursor.execute("SELECT pg_advisory_lock(hashtext(%s))", [schema_name])
            except Exception:
                # DB may not support advisory locks; continue without locking.
                pass
    except Exception:
        # If acquiring the lock fails at connection level, continue.
        pass

    try:
        yield
    finally:
        try:
            with connection.cursor() as cursor:
                try:
                    cursor.execute("SELECT pg_advisory_unlock(hashtext(%s))", [schema_name])
                except Exception:
                    pass
        except Exception:
            pass


def set_search_path_on_cursor(schema_name: str):
    """Set the `search_path` on a fresh DB cursor to the given schema.

    This helps ensure the underlying cursor used by management commands
    operates with the intended schema search_path.
    """
    try:
        with connection.cursor() as cursor:
            try:
                cursor.execute("SET search_path TO %s", [schema_name])
            except Exception:
                # Some DB drivers may not accept identifier parameters; ignore.
                pass
    except Exception:
        pass
