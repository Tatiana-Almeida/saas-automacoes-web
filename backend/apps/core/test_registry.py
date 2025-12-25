from typing import Dict

# In-process registry to help tests where ORM rows created inside the
# pytest transaction are not visible to view-handling DB connections.
# Maps lowercase username/email -> pk
TEST_USER_REGISTRY: Dict[str, int] = {}


def register_user_instance(instance, created, **kwargs):
    if not created:
        return
    # Prefer username, fall back to email
    uname = getattr(instance, "username", None) or getattr(instance, "email", None)
    if not uname:
        return
    try:
        TEST_USER_REGISTRY[uname.lower()] = int(getattr(instance, "pk"))
    except Exception:
        pass


def get_user_pk_by_username(username: str):
    if not username:
        return None
    return TEST_USER_REGISTRY.get(username.lower())
