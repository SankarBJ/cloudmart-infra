"""DB layer: Postgres when reachable, graceful in-memory fallback for tests/CI.
Keeps the app bootable without a database while using real SQL when available."""
import os
import time
import copy

USE_DB = os.environ.get("USE_DB", "auto").lower()  # auto|on|off
_db_status = {"mode": "unknown", "latency_ms": None, "error": None, "products": 0}
_conn = None


def _want_db():
    return USE_DB in ("auto", "on")


def get_conn():
    global _conn
    if not _want_db():
        return None
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        url = os.environ.get("DATABASE_URL")
        t = time.time()
        if url:
            _conn = _conn or psycopg2.connect(url, cursor_factory=RealDictCursor)
        else:
            _conn = _conn or psycopg2.connect(
                host=os.environ.get("DB_HOST", "localhost"),
                database=os.environ.get("DB_NAME", "cloudmart"),
                user=os.environ.get("DB_USER", "cloudmart"),
                password=os.environ.get("DB_PASS", "cloudmart_password"),
                port=os.environ.get("DB_PORT", "5432"),
                cursor_factory=RealDictCursor, connect_timeout=2)
        # validate + ping
        cur = _conn.cursor()
        cur.execute("SELECT 1")
        cur.fetchone()
        _db_status.update(mode="postgres", latency_ms=round((time.time() - t) * 1000, 1), error=None)
        try:
            cur.execute("SELECT COUNT(*) AS c FROM products")
            _db_status["products"] = cur.fetchone()["c"]
        except Exception:
            _conn.rollback()
        cur.close()
        try:
            _conn.commit()
        except Exception:
            pass
        return _conn
    except Exception as e:
        _db_status.update(mode="memory-fallback", error=str(e)[:200], latency_ms=None)
        try:
            if _conn:
                _conn.close()
        except Exception:
            pass
        _conn = None
        if USE_DB == "on":
            raise
        return None


def db_status():
    get_conn()
    return dict(_db_status)


def rows(cur):
    out = []
    for r in cur.fetchall():
        out.append(dict(r))
    return out
