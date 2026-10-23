"""Comprehensive Test Suite validating all 12 Hackathon Core Requirements."""
import os
import sys
import re
import json
import math
import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from fastapi.testclient import TestClient


# ==============================================================================
# Requirement 1: Trusted Control Plane (docker-compose & Dockerfile)
# ==============================================================================
def test_req_01_docker_compose_and_dockerfile():
    compose_path = os.path.join(REPO_ROOT, "docker-compose.yml")
    dockerfile_path = os.path.join(REPO_ROOT, "Dockerfile")
    assert os.path.exists(compose_path), "docker-compose.yml must exist at repo root"
    assert os.path.exists(dockerfile_path), "Dockerfile must exist at repo root"

    with open(compose_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Confirm services api and ledger exist
    assert "api:" in content, "api service must be defined in docker-compose.yml"
    assert "ledger:" in content, "ledger service must be defined in docker-compose.yml"

    # Confirm healthchecks
    assert "pg_isready" in content, "ledger healthcheck must use pg_isready"
    assert "curl -f http://localhost:8080/health" in content, "api healthcheck must curl /health"
    assert "interval:" in content and "timeout:" in content and "retries:" in content, "Healthchecks must define interval, timeout, retries"

    # Confirm ledger mounts ./seeds
    assert "./seeds:/docker-entrypoint-initdb.d" in content, "ledger must mount ./seeds"


# ==============================================================================
# Requirement 2: Environment File (.env.example & NO .env)
# ==============================================================================
def test_req_02_environment_file():
    example_path = os.path.join(REPO_ROOT, ".env.example")
    live_env_path = os.path.join(REPO_ROOT, ".env")

    assert os.path.exists(example_path), ".env.example must exist at repo root"
    assert not os.path.exists(live_env_path), "A live .env file must NOT exist at repo root"

    with open(example_path, "r", encoding="utf-8") as f:
        content = f.read()

    required_keys = [
        "CELESTO_PROVIDER",
        "CELESTO_API_KEY",
        "LLM_API_KEY",
        "LLM_MODEL",
        "DATABASE_URL",
        "API_PORT"
    ]
    for key in required_keys:
        assert f"{key}=" in content, f"Key {key} must be documented in .env.example"


# ==============================================================================
# Requirement 3: Problem Statement (reports/problem.json)
# ==============================================================================
def test_req_03_problem_statement():
    path = os.path.join(REPO_ROOT, "reports", "problem.json")
    assert os.path.exists(path), "reports/problem.json must exist"

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "who" in data and len(data["who"]) >= 40, "who must be at least 40 characters"
    assert "agent_work" in data and len(data["agent_work"]) >= 40, "agent_work must be at least 40 characters"
    assert "proof_output" in data and len(data["proof_output"]) >= 20, "proof_output must be at least 20 characters"
    assert data.get("idea_source") in ["idea_bank", "original"], "idea_source must be 'idea_bank' or 'original'"


# ==============================================================================
# Requirement 4: Audited Command Log (logs/commands.jsonl)
# ==============================================================================
def test_req_04_command_audit_log():
    path = os.path.join(REPO_ROOT, "logs", "commands.jsonl")
    assert os.path.exists(path), "logs/commands.jsonl must exist"

    lines = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                lines.append(json.loads(line))

    assert len(lines) >= 1, "logs/commands.jsonl must contain at least one line"

    name_regex = re.compile(r"^sbx-[a-z0-9]{8,}$")
    for obj in lines:
        assert "ts" in obj and isinstance(obj["ts"], str), "Every line must have ISO-8601 ts"
        assert name_regex.match(obj.get("sandbox_name", "")), f"sandbox_name {obj.get('sandbox_name')} must match ^sbx-[a-z0-9]{{8,}}$"
        assert obj.get("command") and isinstance(obj["command"], str), "command must be non-empty string"
        assert obj.get("decision") in ["allow", "block"], "decision must be 'allow' or 'block'"
        assert obj.get("execution_target") == "celesto_sandbox", "execution_target must be strictly 'celesto_sandbox'"


# ==============================================================================
# Requirement 5: Celesto Capabilities (reports/capabilities.json)
# ==============================================================================
def test_req_05_celesto_capabilities():
    path = os.path.join(REPO_ROOT, "reports", "capabilities.json")
    assert os.path.exists(path), "reports/capabilities.json must exist"

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    caps = data.get("capabilities", [])
    assert len(caps) >= 2, "capabilities must contain at least 2 objects"

    allowed_ids = {
        "persistence", "snapshots", "celestofs", "browser", "published_ports",
        "network_policy", "safety_hooks", "host_mounts", "coding_agent_preset", "agentor_durable"
    }

    seen_ids = set()
    for cap in caps:
        cap_id = cap.get("id")
        assert cap_id in allowed_ids, f"Capability id '{cap_id}' must be in allowed set"
        assert cap_id not in seen_ids, f"Capability id '{cap_id}' must be unique"
        seen_ids.add(cap_id)

        assert len(cap.get("why", "")) >= 80, f"Capability {cap_id} 'why' must be at least 80 characters"
        
        evidence_path = cap.get("evidence_path", "")
        full_evidence_path = os.path.join(REPO_ROOT, evidence_path)
        assert os.path.exists(full_evidence_path), f"evidence_path '{evidence_path}' must exist in repository"


# ==============================================================================
# Requirement 6: Lifecycle Hygiene (reports/lifecycle.json)
# ==============================================================================
def test_req_06_lifecycle_hygiene():
    path = os.path.join(REPO_ROOT, "reports", "lifecycle.json")
    assert os.path.exists(path), "reports/lifecycle.json must exist"

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data.get("cleanup_on_success") is True, "cleanup_on_success must be true"
    assert data.get("cleanup_on_failure") is True, "cleanup_on_failure must be true"
    assert data.get("cleanup_on_interrupt") is True, "cleanup_on_interrupt must be true"

    sandbox_names = data.get("sandbox_names", [])
    assert len(sandbox_names) > 0, "sandbox_names must be non-empty"

    name_regex = re.compile(r"^sbx-[a-z0-9]{8,}$")
    assert len(sandbox_names) == len(set(sandbox_names)), "sandbox_names must be unique"

    # Verify every name matches regex and exists in commands log or reliability file
    commands_path = os.path.join(REPO_ROOT, "logs", "commands.jsonl")
    with open(commands_path, "r", encoding="utf-8") as f:
        commands_content = f.read()

    for name in sandbox_names:
        assert name_regex.match(name), f"Name {name} must match ^sbx-[a-z0-9]{{8,}}$"
        assert name in commands_content, f"Sandbox name {name} must appear in logs/commands.jsonl"


# ==============================================================================
# Requirement 7: Reliability & Postmortem (reports/reliability.json & reports/postmortem.md)
# ==============================================================================
def test_req_07_reliability_and_postmortem():
    rel_path = os.path.join(REPO_ROOT, "reports", "reliability.json")
    post_path = os.path.join(REPO_ROOT, "reports", "postmortem.md")

    assert os.path.exists(rel_path), "reports/reliability.json must exist"
    assert os.path.exists(post_path), "reports/postmortem.md must exist"

    with open(post_path, "r", encoding="utf-8") as f:
        post_content = f.read()
    assert len(post_content) >= 200, "reports/postmortem.md must be at least 200 characters"

    with open(rel_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    runs = data.get("runs", [])
    run_count = data.get("run_count")
    assert run_count >= 20, "run_count must be at least 20"
    assert len(runs) == run_count, "run_count must equal length of runs"

    name_regex = re.compile(r"^sbx-[a-z0-9]{8,}$")
    names = []
    successes = 0
    wall_clocks = []
    boot_times = []
    costs = []

    for r in runs:
        s_name = r.get("sandbox_name", "")
        assert name_regex.match(s_name), f"Sandbox name {s_name} must match regex"
        names.append(s_name)

        assert r.get("fresh") is True, "fresh must be true for all runs"
        if r.get("success") is True:
            successes += 1

        assert r.get("wall_clock_s", -1) >= 0, "wall_clock_s must be >= 0"
        assert r.get("boot_to_ready_s", -1) >= 0, "boot_to_ready_s must be >= 0"
        assert r.get("cost_usd", -1) >= 0, "cost_usd must be >= 0"

        wall_clocks.append(r["wall_clock_s"])
        boot_times.append(r["boot_to_ready_s"])
        costs.append(r["cost_usd"])

    assert len(names) == len(set(names)), "sandbox names must be unique"

    # Arithmetic checks
    expected_success_rate = successes / run_count
    assert abs(data.get("success_rate", 0) - expected_success_rate) <= 0.001, "success_rate calculation error"

    sorted_wall_clocks = sorted(wall_clocks)
    # For 20 rows: 1-based index 10 and 11 => 0-based index 9 and 10
    expected_median_wc = (sorted_wall_clocks[9] + sorted_wall_clocks[10]) / 2.0
    assert abs(data.get("median_wall_clock_s", 0) - expected_median_wc) <= 0.001, "median_wall_clock_s calculation error"

    # p90: 1-based index ceil(0.90 * 20) = 18 => 0-based index 17
    expected_p90_wc = sorted_wall_clocks[17]
    assert abs(data.get("p90_wall_clock_s", 0) - expected_p90_wc) <= 0.001, "p90_wall_clock_s calculation error"

    sorted_boot_times = sorted(boot_times)
    expected_median_btr = (sorted_boot_times[9] + sorted_boot_times[10]) / 2.0
    assert abs(data.get("median_boot_to_ready_s", 0) - expected_median_btr) <= 0.001, "median_boot_to_ready_s calculation error"

    expected_total_cost = sum(costs)
    assert abs(data.get("total_cost_usd", 0) - expected_total_cost) <= 0.01, "total_cost_usd calculation error"


# ==============================================================================
# Requirement 8: Containment Test (reports/containment.json)
# ==============================================================================
def test_req_08_containment_test():
    path = os.path.join(REPO_ROOT, "reports", "containment.json")
    assert os.path.exists(path), "reports/containment.json must exist"

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data.get("attack") in ["prompt_injection_exfil", "destructive_command", "suspicious_package"], "Invalid attack type"
    assert data.get("blocked") is True, "blocked must be true"
    assert data.get("host_untouched") is True, "host_untouched must be true"

    evidence_paths = data.get("evidence_paths", [])
    assert len(evidence_paths) >= 1, "evidence_paths must have at least one entry"
    for p in evidence_paths:
        full_p = os.path.join(REPO_ROOT, p)
        assert os.path.exists(full_p), f"evidence file {p} must exist"


# ==============================================================================
# Requirement 9: Step 7 of 10 Failure Policy (reports/failure_policy.json & trace)
# ==============================================================================
def test_req_09_failure_policy_and_trace():
    policy_path = os.path.join(REPO_ROOT, "reports", "failure_policy.json")
    assert os.path.exists(policy_path), "reports/failure_policy.json must exist"

    with open(policy_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data.get("failed_step") == 7, "failed_step must be 7"
    assert data.get("total_steps") == 10, "total_steps must be 10"
    policy = data.get("policy")
    assert policy in ["resume", "rollback", "fresh"], "policy must be resume, rollback, or fresh"
    assert len(data.get("rationale", "")) >= 200, "rationale must be at least 200 characters"

    trace_path = os.path.join(REPO_ROOT, data.get("trace_path", ""))
    assert os.path.exists(trace_path), f"trace_path {trace_path} must exist"

    found_policy_applied = False
    with open(trace_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                obj = json.loads(line)
                if obj.get("event") == "policy_applied" and obj.get("policy") == policy:
                    found_policy_applied = True
                    break

    assert found_policy_applied, f"trace must contain event equal to policy_applied with policy {policy}"


# ==============================================================================
# Requirement 10: Concurrency Test (reports/concurrency.json)
# ==============================================================================
def test_req_10_concurrency_test():
    path = os.path.join(REPO_ROOT, "reports", "concurrency.json")
    assert os.path.exists(path), "reports/concurrency.json must exist"

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    jobs = data.get("jobs", [])
    assert len(jobs) >= 5, "jobs must have at least 5 objects"

    name_regex = re.compile(r"^sbx-[a-z0-9]{8,}$")
    seen_names = set()
    for job in jobs:
        name = job.get("sandbox_name", "")
        assert name_regex.match(name), f"Sandbox name {name} must match regex"
        assert name not in seen_names, f"Sandbox name {name} must be unique"
        seen_names.add(name)

        started_at = job.get("started_at", "")
        assert isinstance(started_at, str) and len(started_at) > 0, "started_at must be non-empty string"

    assert len(data.get("breakage_notes", "")) >= 40, "breakage_notes must be at least 40 characters"


# ==============================================================================
# Requirement 11: Run Ledger API Contracts (FastAPI TestClient)
# ==============================================================================
def test_req_11_run_ledger_api_endpoints():
    from app.main import app
    client = TestClient(app)

    # 1. GET /health
    res = client.get("/health")
    assert res.status_code == 200, "GET /health must return 200"
    assert res.json() == {"status": "ok"}, "GET /health must return {'status': 'ok'}"

    # 2. GET /api/runs (includes sbx-seeddemo1)
    res = client.get("/api/runs")
    assert res.status_code == 200, "GET /api/runs must return 200"
    runs = res.json()
    assert isinstance(runs, list), "GET /api/runs must return a JSON array"
    assert any(r.get("sandbox_name") == "sbx-seeddemo1" for r in runs), "runs must include sbx-seeddemo1"

    # 3. POST /api/runs valid
    valid_payload = {
        "run_id": "test-run-101",
        "sandbox_name": "sbx-testrunner01",
        "problem_id": "prob-test-01",
        "state": "running",
        "execution_target": "celesto_sandbox"
    }
    res = client.post("/api/runs", json=valid_payload)
    assert res.status_code == 201, f"POST /api/runs with valid data must return 201, got {res.status_code}"
    res_data = res.json()
    assert res_data.get("sandbox_name") == "sbx-testrunner01"

    # 4. POST /api/runs invalid execution_target -> 400
    invalid_target_payload = {
        "run_id": "test-run-102",
        "sandbox_name": "sbx-testrunner02",
        "problem_id": "prob-test-02",
        "state": "running",
        "execution_target": "host"
    }
    res = client.post("/api/runs", json=invalid_target_payload)
    assert res.status_code == 400, f"execution_target 'host' must return 400, got {res.status_code}"

    # 5. POST /api/runs invalid sandbox_name -> 400
    invalid_name_payload = {
        "run_id": "test-run-103",
        "sandbox_name": "bad_name",
        "problem_id": "prob-test-03",
        "state": "running",
        "execution_target": "celesto_sandbox"
    }
    res = client.post("/api/runs", json=invalid_name_payload)
    assert res.status_code == 400, f"bad sandbox_name must return 400, got {res.status_code}"

    # 6. POST /api/runs invalid state -> 400
    invalid_state_payload = {
        "run_id": "test-run-104",
        "sandbox_name": "sbx-testrunner04",
        "problem_id": "prob-test-04",
        "state": "invalid_state",
        "execution_target": "celesto_sandbox"
    }
    res = client.post("/api/runs", json=invalid_state_payload)
    assert res.status_code == 400, f"invalid state must return 400, got {res.status_code}"


# ==============================================================================
# Requirement 12: README Phrase Checks
# ==============================================================================
def test_req_12_readme_required_phrases():
    readme_path = os.path.join(REPO_ROOT, "README.md")
    assert os.path.exists(readme_path), "README.md must exist at repo root"

    with open(readme_path, "r", encoding="utf-8") as f:
        readme_text = f.read()

    required_phrases = [
        "Problem statement",
        "How I used Celesto",
        "Eval report",
        "Containment test",
        "State and failure design",
        "Setup"
    ]

    for phrase in required_phrases:
        assert phrase in readme_text, f"Required phrase '{phrase}' must be present in README.md"


# ==============================================================================
# Requirement 13: Hybrid Model Router (Groq for Low-Latency, Gemini for Step 7)
# ==============================================================================
def test_req_13_hybrid_model_router():
    from app.llm_router import HybridModelRouter
    from code.agent.runner import AgentWorkflowRunner

    # 1. Test Routing Condition when both keys are present
    router = HybridModelRouter(
        default_base_url="https://api.groq.com/openai/v1",
        default_api_key="gsk_live_groq_key_test",
        default_model="llama-3.3-70b-versatile",
        gemini_api_key="AIzaSy_live_gemini_key_test",
        gemini_model="gemini-2.5-pro"
    )

    # Standard tool call (Step 3) -> Routed to Groq
    std_decision = router.execute_react_step(step=3, prompt="Run bash command in sandbox", is_mid_task_failure=False)
    assert std_decision["provider"] == "groq", "Standard steps must route to Groq client"
    assert std_decision["model"] == "llama-3.3-70b-versatile"
    assert std_decision["routing_reason"] == "groq_low_latency_tool_execution"

    # Step 7 MidTaskFailure -> Routed to Gemini for reasoning & large context
    fail_decision = router.execute_react_step(
        step=7,
        prompt="Analyze 420-line compilation error trace",
        is_mid_task_failure=True,
        stack_trace="Traceback (most recent call last): ..."
    )
    assert fail_decision["provider"] == "gemini", "Step 7 MidTaskFailure must route to Gemini client"
    assert fail_decision["model"] == "gemini-2.5-pro"
    assert fail_decision["routing_reason"] == "gemini_large_context_reasoning_for_mid_task_failure"

    # 2. Test Safe Fallback if Gemini key is missing
    fallback_router_no_gemini = HybridModelRouter(
        default_api_key="gsk_live_groq_key_test",
        gemini_api_key=""
    )
    routed_client = fallback_router_no_gemini.route(step=7, is_mid_task_failure=True)
    assert routed_client.provider == "groq", "Must safely fallback to Groq when Gemini key is missing"

    # 3. Test Safe Fallback if Groq key is missing
    fallback_router_no_groq = HybridModelRouter(
        default_api_key="",
        gemini_api_key="AIzaSy_live_gemini_key_test"
    )
    routed_client_std = fallback_router_no_groq.route(step=4, is_mid_task_failure=False)
    assert routed_client_std.provider == "gemini", "Must safely fallback to Gemini when Groq key is missing"

    # 4. Test AgentWorkflowRunner execution with Hybrid Router
    agent_runner = AgentWorkflowRunner("sbx-hybridtest01", router=router)
    result = agent_runner.run_pipeline()
    assert result["final_state"] == "deleted"
    
    # Verify Step 7 in trace used Gemini
    step7_trace = next(ev for ev in result["trace"] if ev.get("step") == 7 and ev.get("event") == "step_failed")
    assert step7_trace.get("llm_provider") == "gemini"
    assert step7_trace.get("routing_reason") == "gemini_large_context_reasoning_for_mid_task_failure"

    # Verify standard step used Groq
    step4_trace = next(ev for ev in result["trace"] if ev.get("step") == 4)
    assert step4_trace.get("llm_provider") == "groq"

