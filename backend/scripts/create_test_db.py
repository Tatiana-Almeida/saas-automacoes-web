import sys
import os
import psycopg2

# Read connection info from env or fallback to sensible defaults
DB_USER = os.getenv('TEST_DB_USER', os.getenv('PGUSER', 'root'))
DB_PASS = os.getenv('TEST_DB_PASSWORD', os.getenv('PGPASSWORD', '1234567890'))
DB_HOST = os.getenv('TEST_DB_HOST', os.getenv('PGHOST', 'localhost'))
DB_PORT = os.getenv('TEST_DB_PORT', os.getenv('PGPORT', '5432'))
DB_TEMPLATE = os.getenv('TEST_DB_NAME', 'saas_test')

try:
    conn = psycopg2.connect(dbname='postgres', user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM pg_database WHERE datname=%s;", (DB_TEMPLATE,))
    row = cur.fetchone()
    if row is None:
        cur.execute(f"CREATE DATABASE {DB_TEMPLATE};")
        print('DB_CREATED')
    else:
        print('DB_EXISTS')
    cur.close()
    conn.close()
except Exception as e:
    print('ERROR', e)
    sys.exit(1)
