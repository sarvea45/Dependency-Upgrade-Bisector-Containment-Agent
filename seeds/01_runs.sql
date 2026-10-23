-- Idempotent schema definition and initial seed for Celesto Run Ledger
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    sandbox_name TEXT NOT NULL UNIQUE,
    problem_id TEXT NOT NULL,
    state TEXT NOT NULL,
    execution_target TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Seed row sbx-seeddemo1 (state: deleted, execution_target: celesto_sandbox)
INSERT INTO runs (run_id, sandbox_name, problem_id, state, execution_target, created_at)
VALUES (
    'run-seed-001',
    'sbx-seeddemo1',
    'prob-dep-bisect',
    'deleted',
    'celesto_sandbox',
    NOW()
)
ON CONFLICT (sandbox_name) DO NOTHING;
