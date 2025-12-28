import psycopg2


def try_conn(host, user, pwd, db):
    try:
        conn = psycopg2.connect(
            host=host, user=user, password=pwd, dbname=db, connect_timeout=5
        )
        cur = conn.cursor()
        cur.execute("SELECT version()")
        cur.close()
        conn.close()
    except Exception:
        pass


if __name__ == "__main__":
    user = "saas_user"
    pwd = "1234567890"
    db = "saas_automacoes_web"

    for host in ("localhost", "127.0.0.1", "172.17.0.2"):
        try_conn(host, user, pwd, db)
