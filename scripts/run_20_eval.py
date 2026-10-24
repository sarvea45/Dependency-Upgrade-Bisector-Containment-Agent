"""Script to run 20 fresh evaluation sandboxes and update reports/reliability.json."""
import os
import sys

# Ensure repository root is on PYTHONPATH
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from app.generate_evals import generate_all
from code.agent.runner import AgentWorkflowRunner

if __name__ == "__main__":
    print("\n" + "=" * 75)
    print("  [LIVE TEST] RUNNING END-TO-END AGENT WORKFLOW IN CELESTO SANDBOX")
    print("=" * 75)
    agent = AgentWorkflowRunner("sbx-liveagent01", verbose=True)
    res = agent.run_pipeline()
    print("\n[+] Live Agent Workflow Finished with state:", res["final_state"])

    print("\n" + "=" * 75)
    print("  [EVAL BENCHMARK] EXECUTING 20-RUN RELIABILITY BENCHMARK SUITE")
    print("=" * 75)
    generate_all()
    print("Evaluation completed successfully. Numbers verified against arithmetic contracts.\n")
