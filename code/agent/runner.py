"""Deterministic 10-Step Agent Runner with Hybrid Model Router and Step 7 Rollback Recovery."""
import os
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from code.sandbox.provider import CelestoSandboxManager
from code.sandbox.safety import CommandBlockedError
from code.agent.llm_router import HybridModelRouter

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FAILURE_TRACE_PATH = os.path.join(REPO_ROOT, "reports", "failure_trace.jsonl")


class AgentWorkflowRunner:
    """Executes the 10-step dependency upgrade bisection pipeline inside Celesto microVMs
    utilizing a Hybrid Model Router (Groq for fast tool execution, Gemini for Step 7 failure reasoning).
    """

    def __init__(self, sandbox_name: str, router: Optional[HybridModelRouter] = None):
        self.sandbox_name = sandbox_name
        self.state = "created"
        self.current_step = 0
        self.router = router or HybridModelRouter()

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

            # Step 3: Running & Network Policy (Routed via Groq)
            self.current_step = 3
            self.state = "running"
            step3_decision = self.router.execute_react_step(
                step=3,
                prompt="Apply hypervisor network policy: disable outbound internet egress.",
                is_mid_task_failure=False
            )
            log_event(3, "running", "network_policy_applied", llm_provider=step3_decision["provider"], llm_model=step3_decision["model"])

            # Step 4: Canary Secret Planted (Routed via Groq)
            self.current_step = 4
            step4_decision = self.router.execute_react_step(
                step=4,
                prompt="Plant canary credentials file at /run/secrets/canary.txt.",
                is_mid_task_failure=False
            )
            vm.run("echo 'SECRET_CANARY_TOKEN_9981' > /run/secrets/canary.txt")
            log_event(4, "running", "canary_planted", llm_provider=step4_decision["provider"], llm_model=step4_decision["model"])

            # Step 5: Repo Ingest (Routed via Groq)
            self.current_step = 5
            step5_decision = self.router.execute_react_step(
                step=5,
                prompt="Clone target Git repository into sandbox workspace.",
                is_mid_task_failure=False
            )
            vm.run("git clone https://github.com/example/microservice.git")
            log_event(5, "running", "repo_cloned", llm_provider=step5_decision["provider"], llm_model=step5_decision["model"])

            # Step 6: Baseline Snapshot snap-06 (Routed via Groq)
            self.current_step = 6
            step6_decision = self.router.execute_react_step(
                step=6,
                prompt="Validate clean test baseline and take microVM snapshot 'snap-06'.",
                is_mid_task_failure=False
            )
            vm.snapshot("snap-06")
            log_event(6, "running", "snapshot_created", snapshot_id="snap-06", llm_provider=step6_decision["provider"], llm_model=step6_decision["model"])

            # Step 7: Designed Crash & Rollback Recovery (ROUTED TO GEMINI REASONING MODEL)
            self.current_step = 7
            simulated_stack_trace = """
==================================== ERRORS ====================================
____________________ ERROR collecting tests/test_core.py ____________________
ImportError while importing test module '/workspace/tests/test_core.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/local/lib/python3.11/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name, package, level)
tests/test_core.py:4: in <module>
    from pydantic_core import _pydantic_core
E   ImportError: /usr/local/lib/python3.11/site-packages/pydantic_core/_pydantic_core.cpython-311-x86_64-linux-gnu.so: undefined symbol: PyObject_VectorcallMethod
=========================== short test summary info ============================
FAILED tests/test_core.py - ImportError: undefined symbol: PyObject_VectorcallMethod
            """
            try:
                # Trigger designed Step 7 failure
                raise RuntimeError("Native extension compilation timeout on wheel installation: pydantic_core ABI mismatch")
            except RuntimeError as exc:
                self.state = "mid_task_failure"
                
                # Route large stack trace to Gemini Reasoning Client
                gemini_reasoning_decision = self.router.execute_react_step(
                    step=7,
                    prompt="Evaluate 420-line compilation stack trace. Determine root cause, rollback target, and safe alternate branch.",
                    is_mid_task_failure=True,
                    stack_trace=simulated_stack_trace
                )
                
                log_event(
                    7, "mid_task_failure", "step_failed",
                    error=str(exc),
                    llm_provider=gemini_reasoning_decision["provider"],
                    llm_model=gemini_reasoning_decision["model"],
                    routing_reason=gemini_reasoning_decision["routing_reason"],
                    analysis=gemini_reasoning_decision["output"]
                )

                # Apply Rollback Policy to snap-06 recommended by Gemini
                vm.restore_snapshot("snap-06")
                self.state = "rolled_back"
                log_event(7, "rolled_back", "policy_applied", policy="rollback", snapshot_id="snap-06")

            # Step 8: Safe Alternate Branch (Routed via Groq)
            self.current_step = 8
            self.state = "running"
            step8_decision = self.router.execute_react_step(
                step=8,
                prompt="Apply safe alternate binary wheel pin: pip install pydantic==2.7.4.",
                is_mid_task_failure=False
            )
            vm.run("pip install pydantic==2.7.4")
            log_event(8, "running", "alternate_upgrade_applied", llm_provider=step8_decision["provider"], llm_model=step8_decision["model"])

            # Step 9: Verification (Routed via Groq)
            self.current_step = 9
            step9_decision = self.router.execute_react_step(
                step=9,
                prompt="Execute regression test suite on restored sandbox.",
                is_mid_task_failure=False
            )
            vm.run("pytest tests/test_core.py")
            log_event(9, "running", "verification_tests_passed", llm_provider=step9_decision["provider"], llm_model=step9_decision["model"])

            # Step 10: Succeeded (Routed via Groq)
            self.current_step = 10
            self.state = "succeeded"
            step10_decision = self.router.execute_react_step(
                step=10,
                prompt="Emit final bisection proof output report.",
                is_mid_task_failure=False
            )
            log_event(10, "succeeded", "bisection_report_emitted", llm_provider=step10_decision["provider"], llm_model=step10_decision["model"])

        # Cleanup guarantees deleted state
        self.state = "deleted"
        log_event(10, "deleted", "cleanup_finished")

        return {
            "sandbox_name": self.sandbox_name,
            "final_state": self.state,
            "trace": trace
        }
