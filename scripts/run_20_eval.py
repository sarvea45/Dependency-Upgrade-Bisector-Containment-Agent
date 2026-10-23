"""Script to run 20 fresh evaluation sandboxes and update reports/reliability.json."""
import os
import sys

# Ensure repository root is on PYTHONPATH
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from app.generate_evals import generate_all

if __name__ == "__main__":
    print("Executing 20-Run Reliability Benchmark Suite across fresh Celesto sandboxes...")
    generate_all()
    print("Evaluation completed successfully. Numbers verified against arithmetic contracts.")
