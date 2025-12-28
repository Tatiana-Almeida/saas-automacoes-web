import psycopg2

try:
    conn = psycopg2.connect(
        host="localhost", user="postgres", password="postgres", dbname="postgres"
    )
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("ALTER ROLE saas_user CREATEDB;")
    cur.close()
    conn.close()
except Exception:
    pass
