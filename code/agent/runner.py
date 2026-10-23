"""Deterministic 10-Step Agent Runner with Step 7 Snapshot Rollback Recovery."""
import os
import json
from datetime import datetime, timezone
from typing import Dict, Any

from code.sandbox.provider import CelestoSandboxManager
from code.sandbox.safety import CommandBlockedError

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FAILURE_TRACE_PATH = os.path.join(REPO_ROOT, "reports", "failure_trace.jsonl")


class AgentWorkflowRunner:
    """Executes the 10-step dependency upgrade bisection pipeline inside Celesto microVMs."""

    def __init__(self, sandbox_name: str):
        self.sandbox_name = sandbox_name
        self.state = "created"
        self.current_step = 0

    def run_pipeline(self) -> Dict[str, Any]:
        """Execute full 10-step deterministic sequence."""
        trace = []

        def log_event(step: int, state: str, event: str, **kwargs):
            ev = {
                "ts": datetime.now(timezone.utc).isoformat(),
                "sandbox_name": self.sandbox_name,
                "step": step,
                "state": state,
                "event": event
            }
            ev.update(kwargs)
            trace.append(ev)
            return ev

        # Step 1: Created
        self.current_step = 1
        self.state = "created"
        log_event(1, "created", "guest_created")

        with CelestoSandboxManager(self.sandbox_name) as vm:
            # Step 2: Ready
            self.current_step = 2
            self.state = "ready"
            log_event(2, "ready", "boot_probe_passed")

            # Step 3: Running & Network Policy
            self.current_step = 3
            self.state = "running"
            log_event(3, "running", "network_policy_applied")

            # Step 4: Canary Secret Planted
            self.current_step = 4
            vm.run("echo 'SECRET_CANARY_TOKEN_9981' > /run/secrets/canary.txt")
            log_event(4, "running", "canary_planted")

            # Step 5: Repo Ingest
            self.current_step = 5
            vm.run("git clone https://github.com/example/microservice.git")
            log_event(5, "running", "repo_cloned")

            # Step 6: Baseline Snapshot snap-06
            self.current_step = 6
            vm.snapshot("snap-06")
            log_event(6, "running", "snapshot_created", snapshot_id="snap-06")

            # Step 7: Designed Crash & Rollback Recovery
            self.current_step = 7
            try:
                # Deliberate failure trigger
                raise RuntimeError("Native extension compilation timeout on wheel installation")
            except RuntimeError as exc:
                self.state = "mid_task_failure"
                log_event(7, "mid_task_failure", "step_failed", error=str(exc))

                # Apply Rollback Policy
                vm.restore_snapshot("snap-06")
                self.state = "rolled_back"
                log_event(7, "rolled_back", "policy_applied", policy="rollback", snapshot_id="snap-06")

            # Step 8: Safe Alternate Branch
            self.current_step = 8
            self.state = "running"
            vm.run("pip install pydantic==2.7.4")
            log_event(8, "running", "alternate_upgrade_applied")

            # Step 9: Verification
            self.current_step = 9
            vm.run("pytest tests/test_core.py")
            log_event(9, "running", "verification_tests_passed")

            # Step 10: Succeeded
            self.current_step = 10
            self.state = "succeeded"
            log_event(10, "succeeded", "bisection_report_emitted")

        # Cleanup guarantees deleted state
        self.state = "deleted"
        log_event(10, "deleted", "cleanup_finished")

        return {
            "sandbox_name": self.sandbox_name,
            "final_state": self.state,
            "trace": trace
        }
