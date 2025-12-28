"""Test utilities for tenant creation.

This module consolidates the public test helper API for creating tenants so
tests import from a stable path: `tests.utils.tenants.create_tenant`.

It re-exports the existing helper implemented in `tests/helpers/tenant.py`.
"""

from ..helpers.tenant import create_tenant

__all__ = ["create_tenant"]
