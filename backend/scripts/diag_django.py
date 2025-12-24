#!/usr/bin/env python3
"""Simple Django project diagnostic script.

Checks INSTALLED_APPS ordering, AUTH_USER_MODEL and existence of users table in Postgres.

Usage:
  python scripts/diag_django.py --settings /path/to/settings.py --db "postgres://..."

"""
import argparse
import ast
import sys
import psycopg2


def parse_settings(path):
    with open(path, 'r', encoding='utf-8') as f:
        src = f.read()
    tree = ast.parse(src, filename=path)
    installed_apps = None
    auth_user_model = None
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == 'INSTALLED_APPS':
                    # Expect a list or tuple literal
                    val = node.value
                    apps = []
                    if isinstance(val, (ast.List, ast.Tuple)):
                        for elt in val.elts:
                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                apps.append(elt.value)
                            elif isinstance(elt, ast.Str):
                                apps.append(elt.s)
                    installed_apps = apps
                if isinstance(target, ast.Name) and target.id == 'AUTH_USER_MODEL':
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
    except Exception as e:
        print(f"ERROR: could not connect to database: {e}")
        return None


def main():
    p = argparse.ArgumentParser(description='Django project diagnostic')
    p.add_argument('--settings', '-s', required=True, help='Path to settings.py')
    p.add_argument('--db', '-d', required=True, help='Postgres connection string (DSN)')
    args = p.parse_args()

    settings_path = args.settings
    dsn = args.db

    print(f"Reading settings from: {settings_path}")
    installed_apps, auth_user_model = parse_settings(settings_path)

    if installed_apps is None:
        print("Could not parse INSTALLED_APPS from settings.py")
    else:
        print(f"Found INSTALLED_APPS (first 10): {installed_apps[:10]}")
        try:
            idx_users = installed_apps.index('users')
        except ValueError:
            idx_users = None
        try:
            idx_admin = installed_apps.index('django.contrib.admin')
        except ValueError:
            idx_admin = None

        if idx_users is None:
            print("- users app: NOT FOUND in INSTALLED_APPS")
        elif idx_admin is None:
            print("- django.contrib.admin: NOT FOUND in INSTALLED_APPS")
        else:
            if idx_users < idx_admin:
                print("- Order: OK — 'users' appears before 'django.contrib.admin'")
            else:
                print("- Order: WRONG — 'users' appears AFTER 'django.contrib.admin'")

    if auth_user_model is None:
        print("Could not parse AUTH_USER_MODEL from settings.py")
    else:
        print(f"Found AUTH_USER_MODEL = '{auth_user_model}'")
        if auth_user_model == 'users.User':
            print("- AUTH_USER_MODEL: OK")
        else:
            print("- AUTH_USER_MODEL: WRONG (expected 'users.User')")

    # Determine expected table name for users.User
    expected_table = 'users_user'
    print(f"Checking for table '{expected_table}' in database...")
    exists = check_table_exists(dsn, f'public.{expected_table}')
    if exists is True:
        print(f"- Table exists: {expected_table}")
    elif exists is False:
        print(f"- Table NOT found: {expected_table}")
    else:
        print("- Table check could not be completed due to DB error")


if __name__ == '__main__':
    main()
