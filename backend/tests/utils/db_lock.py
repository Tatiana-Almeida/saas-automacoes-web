import hashlib
import os
import sys
import tempfile
from contextlib import contextmanager

from django.db import connection


def _file_lock_path(schema_name: str) -> str:
    # Safe filename derived from schema name
    h = hashlib.sha1(schema_name.encode("utf-8")).hexdigest()
    return os.path.join(tempfile.gettempdir(), f"pytest_tenant_lock_{h}.lock")


@contextmanager
def advisory_lock(schema_name: str):
    """Acquire a Postgres advisory lock or fall back to a filesystem lock.

    Prefer Postgres advisory locks (fast, per-database). If unavailable
    (non-Postgres or permission issues), attempt a simple file lock using
    OS-specific primitives. The file lock is a best-effort fallback to
    serialize cross-process operations on the same host.
    """
    file_handle = None
    locked_via_db = False

    # Try DB advisory lock first
    try:
        with connection.cursor() as cursor:
            try:
                cursor.execute("SELECT pg_advisory_lock(hashtext(%s))", [schema_name])
                locked_via_db = True
            except Exception:
                locked_via_db = False
    except Exception:
        locked_via_db = False

    # If DB lock not acquired, try file lock
    if not locked_via_db:
        path = _file_lock_path(schema_name)
        try:
            # Open file for exclusive creation/append
            file_handle = open(path, "a+")
            if sys.platform == "win32":
                import msvcrt

                try:
                    msvcrt.locking(file_handle.fileno(), msvcrt.LK_LOCK, 1)
                except Exception:
                    pass
            else:
                import fcntl

                try:
                    fcntl.flock(file_handle.fileno(), fcntl.LOCK_EX)
                except Exception:
                    pass
        except Exception:
            file_handle = None

    try:
        yield
    finally:
        # Release DB advisory lock if held
        if locked_via_db:
            try:
                with connection.cursor() as cursor:
                    try:
                        cursor.execute(
                            "SELECT pg_advisory_unlock(hashtext(%s))", [schema_name]
                        )
                    except Exception:
                        pass
            except Exception:
                pass

        # Release and close file lock if used
        if file_handle is not None:
            try:
                if sys.platform == "win32":
                    import msvcrt

                    try:
                        file_handle.seek(0)
                        msvcrt.locking(file_handle.fileno(), msvcrt.LK_UNLCK, 1)
                    except Exception:
                        pass
                else:
                    import fcntl

                    try:
                        fcntl.flock(file_handle.fileno(), fcntl.LOCK_UN)
                    except Exception:
                        pass
            finally:
                try:
                    file_handle.close()
                except Exception:
                    pass


def set_search_path_on_cursor(schema_name: str):
    """Set the `search_path` on a fresh DB cursor to the given schema.

    This helps ensure the underlying cursor used by management commands
    operates with the intended schema search_path.
    """
    # Retry a couple times if the connection is in a transient bad state.
    attempts = 3
    for attempt in range(attempts):
        try:
            with connection.cursor() as cursor:
                try:
                    cursor.execute("SET search_path TO %s", [schema_name])
                except Exception:
                    # Some DB drivers may not accept identifier parameters; ignore.
                    try:
                        cursor.execute(f"SET search_path TO {schema_name}")
                    except Exception:
                        pass
            return
        except Exception:
            # Small backoff before retry
            try:
                import time

                time.sleep(0.05 * (attempt + 1))
            except Exception:
                pass
    # If we reach here, best-effort failed; callers will handle exceptions.
    return
