#!/usr/bin/env python3
"""Simple Django project diagnostic script.

Checks INSTALLED_APPS ordering, AUTH_USER_MODEL and existence of users table in Postgres.

Usage:
  python scripts/diag_django.py --settings /path/to/settings.py --db "postgres://..."

"""

import argparse
import ast

import psycopg2


def parse_settings(path):
    with open(path, "r", encoding="utf-8") as f:
        src = f.read()
    tree = ast.parse(src, filename=path)
    installed_apps = None
    auth_user_model = None
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "INSTALLED_APPS":
                    # Expect a list or tuple literal
                    val = node.value
                    apps = []
                    if isinstance(val, (ast.List, ast.Tuple)):
                        for elt in val.elts:
                            if isinstance(elt, ast.Constant) and isinstance(
                                elt.value, str
                            ):
                                apps.append(elt.value)
                            elif isinstance(elt, ast.Str):
                                apps.append(elt.s)
                    installed_apps = apps
                if isinstance(target, ast.Name) and target.id == "AUTH_USER_MODEL":
                    val = node.value
                    if isinstance(val, ast.Constant) and isinstance(val.value, str):
                        auth_user_model = val.value
                    elif isinstance(val, ast.Str):
                        auth_user_model = val.s
    return installed_apps, auth_user_model


def check_table_exists(dsn, table_name):
    try:
        conn = psycopg2.connect(dsn)
        cur = conn.cursor()
        # Use to_regclass to check; returns null if not found
        cur.execute("select to_regclass(%s);", (table_name,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        return bool(row and row[0])
    except Exception:
        return None


def main():
    p = argparse.ArgumentParser(description="Django project diagnostic")
    p.add_argument("--settings", "-s", required=True, help="Path to settings.py")
    p.add_argument("--db", "-d", required=True, help="Postgres connection string (DSN)")
    args = p.parse_args()

    settings_path = args.settings
    dsn = args.db

    installed_apps, auth_user_model = parse_settings(settings_path)

    if installed_apps is None:
        pass
    else:
        try:
            idx_users = installed_apps.index("users")
        except ValueError:
            idx_users = None
        try:
            idx_admin = installed_apps.index("django.contrib.admin")
        except ValueError:
            idx_admin = None

        if idx_users is None:
            pass
        elif idx_admin is None:
            pass
        else:
            if idx_users < idx_admin:
                pass
            else:
                pass

    if auth_user_model is None:
        pass
    else:
        if auth_user_model == "users.User":
            pass
        else:
            pass

    # Determine expected table name for users.User
    expected_table = "users_user"
    exists = check_table_exists(dsn, f"public.{expected_table}")
    if exists is True:
        pass
    elif exists is False:
        pass
    else:
        pass


if __name__ == "__main__":
    main()
