"""PostgreSQL database connection manager with in-memory resilient fallback."""
import os
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from code.config import DATABASE_URL

# Synchronized seed data cache
_IN_MEMORY_RUNS: Dict[str, Dict[str, Any]] = {
    "sbx-seeddemo1": {
        "run_id": "run-seed-001",
        "sandbox_name": "sbx-seeddemo1",
        "problem_id": "prob-dep-bisect",
        "state": "deleted",
        "execution_target": "celesto_sandbox",
        "created_at": "2026-10-23T07:00:00Z"
    }
}


def _get_pg_conn():
    try:
        import psycopg2
        import psycopg2.extras
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=3)
        conn.autocommit = True
        return conn
    except Exception:
        return None


def init_db():
    """Create runs table and insert seed row if connected."""
    conn = _get_pg_conn()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS runs (
                        run_id TEXT PRIMARY KEY,
                        sandbox_name TEXT NOT NULL UNIQUE,
                        problem_id TEXT NOT NULL,
                        state TEXT NOT NULL,
                        execution_target TEXT NOT NULL,
                        created_at TIMESTAMPTZ DEFAULT NOW()
                    );
                    INSERT INTO runs (run_id, sandbox_name, problem_id, state, execution_target, created_at)
                    VALUES ('run-seed-001', 'sbx-seeddemo1', 'prob-dep-bisect', 'deleted', 'celesto_sandbox', NOW())
                    ON CONFLICT (sandbox_name) DO NOTHING;
                """)
        finally:
            conn.close()


def get_all_runs() -> List[Dict[str, Any]]:
    """Retrieve all recorded runs."""
    conn = _get_pg_conn()
    if conn:
        try:
            import psycopg2.extras
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT run_id, sandbox_name, problem_id, state, execution_target, created_at FROM runs ORDER BY created_at ASC")
                rows = cur.fetchall()
                out = []
                for r in rows:
                    d = dict(r)
                    if isinstance(d.get("created_at"), datetime):
                        d["created_at"] = d["created_at"].isoformat()
                    out.append(d)
                return out
        except Exception:
            pass
        finally:
            conn.close()
    return list(_IN_MEMORY_RUNS.values())


def insert_run(run_data: Dict[str, Any]) -> Dict[str, Any]:
    """Store or update run row."""
    now_iso = datetime.now(timezone.utc).isoformat()
    record = {
        "run_id": run_data["run_id"],
        "sandbox_name": run_data["sandbox_name"],
        "problem_id": run_data["problem_id"],
        "state": run_data["state"],
        "execution_target": run_data["execution_target"],
        "created_at": run_data.get("created_at") or now_iso
    }
    conn = _get_pg_conn()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO runs (run_id, sandbox_name, problem_id, state, execution_target, created_at)
                    VALUES (%s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (sandbox_name) DO UPDATE SET
                        problem_id = EXCLUDED.problem_id,
                        state = EXCLUDED.state,
                        execution_target = EXCLUDED.execution_target
                """, (
                    record["run_id"], record["sandbox_name"],
                    record["problem_id"], record["state"], record["execution_target"]
                ))
        except Exception:
            pass
        finally:
            conn.close()

    _IN_MEMORY_RUNS[record["sandbox_name"]] = record
    return record
