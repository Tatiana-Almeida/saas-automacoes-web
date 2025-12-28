def require_permission(code: str):
    """Decorator to set required_permission on function-based views."""

    def decorator(func):
        func.required_permission = code
        return func

    return decorator
