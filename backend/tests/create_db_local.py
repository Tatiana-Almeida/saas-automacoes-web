import psycopg2

try:
    conn = psycopg2.connect(
        host="localhost", user="saas_user", password="1234567890", dbname="postgres"
    )
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("CREATE DATABASE test_saas_conn_check")
    print("Created DB test_saas_conn_check")
    cur.close()
    conn.close()
except Exception as e:
    print("ERR", type(e).__name__, e)
