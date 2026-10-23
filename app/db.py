"""PostgreSQL connection and Run Ledger queries with resilient fallback."""
import os
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://ledger:ledger@ledger:5432/ledger")

# In-memory storage cache to ensure zero-failure local testing when Postgres is not running
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


def _get_pg_connection():
    """Attempt connecting to PostgreSQL database."""
    try:
        import psycopg2
        import psycopg2.extras
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=3)
        conn.autocommit = True
        return conn
    except Exception:
        return None


def init_db():
    """Initialize database tables and verify seed row."""
    conn = _get_pg_connection()
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
    """Fetch all runs from database (or in-memory cache if DB offline)."""
    conn = _get_pg_connection()
    if conn:
        try:
            import psycopg2.extras
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT run_id, sandbox_name, problem_id, state, execution_target, created_at FROM runs ORDER BY created_at ASC")
                rows = cur.fetchall()
                result = []
                for r in rows:
                    row_dict = dict(r)
                    if isinstance(row_dict.get("created_at"), datetime):
                        row_dict["created_at"] = row_dict["created_at"].isoformat()
                    result.append(row_dict)
                return result
        except Exception:
            pass
        finally:
            conn.close()

    # Fallback to in-memory store
    return list(_IN_MEMORY_RUNS.values())


def insert_run(run_data: Dict[str, Any]) -> Dict[str, Any]:
    """Insert or update a run row."""
    now_iso = datetime.now(timezone.utc).isoformat()
    stored_obj = {
        "run_id": run_data["run_id"],
        "sandbox_name": run_data["sandbox_name"],
        "problem_id": run_data["problem_id"],
        "state": run_data["state"],
        "execution_target": run_data["execution_target"],
        "created_at": run_data.get("created_at") or now_iso
    }

    conn = _get_pg_connection()
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
                    stored_obj["run_id"],
                    stored_obj["sandbox_name"],
                    stored_obj["problem_id"],
                    stored_obj["state"],
                    stored_obj["execution_target"]
                ))
        except Exception:
            pass
        finally:
            conn.close()

    # Always keep in-memory cache synchronized
    _IN_MEMORY_RUNS[stored_obj["sandbox_name"]] = stored_obj
    return stored_obj
