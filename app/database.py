import psycopg2
from psycopg2.pool import ThreadedConnectionPool
from psycopg2.extras import RealDictCursor
from types import SimpleNamespace
from flask import g

pool = None
_database_url = None


def init_db(app):
    global pool, _database_url
    new_url = app.config.get("DATABASE_URL") or app.config.get(
        "SQLALCHEMY_DATABASE_URI", "postgresql://localhost/matcha_db"
    )
    if pool is not None and _database_url == new_url:
        app.teardown_appcontext(_teardown)
        return
    if pool is not None:
        try:
            pool.closeall()
        except Exception:
            pass
    _database_url = new_url
    pool = ThreadedConnectionPool(2, 10, _database_url)
    app.teardown_appcontext(_teardown)


def get_db():
    if "db_conn" not in g:
        g.db_conn = pool.getconn()
    return g.db_conn


def _teardown(exc=None):
    conn = g.pop("db_conn", None)
    if conn is not None:
        if exc is None:
            try:
                conn.commit()
            except Exception:
                conn.rollback()
        else:
            conn.rollback()
        pool.putconn(conn)


def query_one(sql, params=None):
    conn = get_db()
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(sql, params)
        row = cur.fetchone()
    return dict(row) if row else None


def query_all(sql, params=None):
    conn = get_db()
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]


def execute(sql, params=None):
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.rowcount


def execute_returning(sql, params=None):
    conn = get_db()
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(sql, params)
        row = cur.fetchone()
    return dict(row) if row else None


def commit():
    conn = g.get("db_conn")
    if conn:
        conn.commit()


def rollback():
    conn = g.get("db_conn")
    if conn:
        conn.rollback()


def to_obj(row):
    if row is None:
        return None
    return SimpleNamespace(**row)


def to_objs(rows):
    return [SimpleNamespace(**r) for r in rows]


def get_raw_conn():
    return psycopg2.connect(_database_url)
